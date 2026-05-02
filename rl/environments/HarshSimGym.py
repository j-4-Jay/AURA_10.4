import os
import gymnasium as gym
from gymnasium import spaces
import numpy as np
import polars as pl
import time

# [AURA-STRICT-PROTOCOL] 
# Global C++ memory pointer. If core 1 loads it, cores 2, 3, and 4 instantly share the exact same memory!
_PARQUET_CACHE = {}

def load_and_cache_data(parquet_path: str):
    """Loads Parquet data, calculates indicators instantly via Polars, and caches as NumPy arrays."""
    global _PARQUET_CACHE
    
    if parquet_path in _PARQUET_CACHE:
        return _PARQUET_CACHE[parquet_path]
        
    print(f"[*] GYM: Fast-Vectorizing Indicators for {os.path.basename(parquet_path)}...")
    
    # 1. Read Data using Lazy Execution for extreme speed
    df = pl.read_parquet(parquet_path)
    
    # Ensure column names are uppercase and strip MT5 brackets (<>)
    rename_map = {col: col.upper().replace('<', '').replace('>', '') for col in df.columns}
    df = df.rename(rename_map)
    
    # Fast column injection without heavy copying
    if "SPREAD" not in df.columns:
        df = df.with_columns(pl.lit(0).alias("SPREAD_RAW"))
    else:
        df = df.with_columns(pl.col("SPREAD").alias("SPREAD_RAW"))
        
    df = df.with_columns((pl.col("CLOSE") * 0.0001).alias("SPREAD"))
    
    # 2. Vectorized Polars Pre-computation (C++ Level Speed)
    df = df.with_columns([
        (pl.col("HIGH") - pl.col("LOW")).rolling_mean(window_size=14).fill_null(0.001).alias("ATR"),
        pl.col("CLOSE").rolling_std(window_size=14).fill_null(0.001).alias("ADX"),
        pl.col("CLOSE").ewm_mean(span=9, adjust=False).alias("EMA_9"),
        pl.col("CLOSE").ewm_mean(span=21, adjust=False).alias("EMA_21"),
        pl.col("CLOSE").ewm_mean(span=50, adjust=False).alias("EMA_50"),
        pl.col("CLOSE").ewm_mean(span=200, adjust=False).alias("EMA_200")
    ])

    # 3. Convert to strict 1D Float32 NumPy arrays (Zero-Copy extraction)
    # Using .to_numpy() on Polars Series is infinitely faster than pandas!
    data_dict = {
        "OPEN": df["OPEN"].to_numpy().astype(np.float32),
        "HIGH": df["HIGH"].to_numpy().astype(np.float32),
        "LOW": df["LOW"].to_numpy().astype(np.float32),
        "CLOSE": df["CLOSE"].to_numpy().astype(np.float32),
        "SPREAD": df["SPREAD"].to_numpy().astype(np.float32),
        "ATR": df["ATR"].to_numpy().astype(np.float32),
        "ADX": df["ADX"].to_numpy().astype(np.float32),
        "EMA_9": df["EMA_9"].to_numpy().astype(np.float32),
        "EMA_21": df["EMA_21"].to_numpy().astype(np.float32),
        "EMA_50": df["EMA_50"].to_numpy().astype(np.float32),
        "EMA_200": df["EMA_200"].to_numpy().astype(np.float32),
    }
    
    _PARQUET_CACHE[parquet_path] = data_dict
    return data_dict

class HarshSimGym(gym.Env):
    """
    A hyper-realistic trading environment that heavily penalizes over-trading.
    Now optimized with Global RAM Caching and pure NumPy execution.
    """
    def __init__(self, parquet_path, initial_balance=10000.0, lot_size=100000, 
                 commission_per_lot=3.0, slippage_pips=0.5, window_size=60):
        super(HarshSimGym, self).__init__()
        
        self.initial_balance = initial_balance
        self.lot_size = lot_size
        self.commission_per_lot = commission_per_lot
        self.slippage_penalty = slippage_pips * 0.0001
        self.window_size = window_size
        
        # Instantly load from shared RAM cache!
        self.data = load_and_cache_data(parquet_path)
        
        self.max_steps = len(self.data["CLOSE"]) - 1
        
        # Actions: 0 = Hold, 1 = Buy, 2 = Sell
        self.action_space = spaces.Discrete(3)
        
        # Features: OHLC Window (4 * window) + State(2) + Radar(8) + Votes(14)
        obs_features = (self.window_size * 4) + 2 + 8 + 14
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(obs_features,), dtype=np.float32)

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        
        self.current_step = self.window_size
        self.balance = self.initial_balance
        self.equity = self.initial_balance
        self.position = 0  # 0=Flat, 1=Long, -1=Short
        self.entry_price = 0.0
        self.trades_executed = 0
        
        return self._get_obs(), {}

    def _get_obs(self):
        start = self.current_step - self.window_size
        end = self.current_step
        
        # 1. Fast Array Slicing
        window = np.column_stack((
            self.data["OPEN"][start:end],
            self.data["HIGH"][start:end],
            self.data["LOW"][start:end],
            self.data["CLOSE"][start:end]
        )).flatten()
        
        # 2. Account State
        floating_pnl = 0.0
        if self.position == 1:
            floating_pnl = (self.data["CLOSE"][self.current_step] - self.entry_price) * self.lot_size
        elif self.position == -1:
            floating_pnl = (self.entry_price - self.data["CLOSE"][self.current_step]) * self.lot_size
            
        state = np.array([self.position, floating_pnl / self.initial_balance], dtype=np.float32)
        
        # 3. Giant Radar (8 metrics)
        radar = np.array([
            self.data["ATR"][self.current_step],
            self.data["ADX"][self.current_step],
            self.data["EMA_9"][self.current_step],
            self.data["EMA_21"][self.current_step],
            self.data["EMA_50"][self.current_step],
            self.data["EMA_200"][self.current_step],
            self.data["SPREAD"][self.current_step],
            0.0 
        ], dtype=np.float32)
        
        # 4. Strategy Votes (14 robots - simulating neutral votes for now)
        votes = np.zeros(14, dtype=np.float32)
        
        return np.concatenate([window, state, radar, votes])

    def step(self, action):
        current_price = self.data["CLOSE"][self.current_step]
        spread = self.data["SPREAD"][self.current_step]
        reward = 0.0
        realized_pnl = 0.0
        illegal_action = False
        
        # Fast Execution Logic
        if action == 1: # BUY
            if self.position <= 0:
                if self.position == -1:
                    realized_pnl = (self.entry_price - current_price - spread - self.slippage_penalty) * self.lot_size - self.commission_per_lot
                    self.balance += realized_pnl
                self.position = 1
                self.entry_price = current_price + spread + self.slippage_penalty
                self.balance -= self.commission_per_lot
                self.trades_executed += 1
            else:
                illegal_action = True
                
        elif action == 2: # SELL
            if self.position >= 0:
                if self.position == 1:
                    realized_pnl = (current_price - self.entry_price - spread - self.slippage_penalty) * self.lot_size - self.commission_per_lot
                    self.balance += realized_pnl
                self.position = -1
                self.entry_price = current_price - spread - self.slippage_penalty
                self.balance -= self.commission_per_lot
                self.trades_executed += 1
            else:
                illegal_action = True
                
        elif action == 0: # CLOSE ALL / HOLD
            if self.position == 1:
                realized_pnl = (current_price - self.entry_price - spread - self.slippage_penalty) * self.lot_size - self.commission_per_lot
                self.balance += realized_pnl
                self.position = 0
                self.trades_executed += 1
            elif self.position == -1:
                realized_pnl = (self.entry_price - current_price - spread - self.slippage_penalty) * self.lot_size - self.commission_per_lot
                self.balance += realized_pnl
                self.position = 0
                self.trades_executed += 1
                
        # Base Reward is just the PnL shift
        reward = realized_pnl / self.initial_balance
        
        self.current_step += 1
        terminated = self.current_step >= self.max_steps
        truncated = False
        
        info = {
            "realized_pnl": realized_pnl,
            "in_trade": self.position != 0,
            "current_position": self.position,
            "illegal_action": illegal_action
        }
        
        return self._get_obs(), float(reward), terminated, truncated, info