import os
import gymnasium as gym
from gymnasium import spaces
import numpy as np
import polars as pl

# ===================================================================
# THE GLOBAL RAM VAULT (SPEED HACK #1)
# This prevents 100 Optuna trials from reading the SSD 100 times.
# It loads the data into RAM once, and all parallel agents share it.
# ===================================================================
_PARQUET_CACHE = {}

def load_and_cache_data(parquet_path: str):
    """Loads Parquet data, calculates indicators instantly via Polars, and caches as NumPy arrays."""
    global _PARQUET_CACHE
    
    if parquet_path in _PARQUET_CACHE:
        return _PARQUET_CACHE[parquet_path]
        
    print(f"[*] GYM: First-time SSD read & Vectorizing Indicators for {os.path.basename(parquet_path)}...")
    
    # 1. Read Data
    df = pl.read_parquet(parquet_path)
    
    # Ensure column names are uppercase and strip MT5 brackets (<>)
    rename_map = {col: col.upper().replace('<', '').replace('>', '') for col in df.columns}
    df = df.rename(rename_map)
    
    # Failsafe for missing standard columns
    if "SPREAD" not in df.columns:
        df = df.with_columns(pl.lit(0).alias("SPREAD_RAW"))
    else:
        df = df.with_columns(pl.col("SPREAD").alias("SPREAD_RAW"))
        
    # SPREAD is in MT5 points (integers). Let's convert it to actual price magnitude.
    # A safe way is to assume typical spreads are roughly 1%-5% of ATR, but we can also infer point size.
    # For now, let's just make the spread a constant 5% of ATR to be universally fair and dynamic,
    # OR we can cap the MT5 spread if it's insanely large. 
    # Let's dynamically scale MT5 SPREAD points:
    # We will just use 0.00015 for forex and proportional for Crypto by taking 0.01% of Close.
    df = df.with_columns((pl.col("CLOSE") * 0.0001).alias("SPREAD"))
    
    # 2. Vectorized Polars Pre-computation (SPEED HACK #2)
    # Calculate Institutional Indicators instantly across millions of rows in C++
    df = df.with_columns([
        # ATR Proxy (14-period rolling High - Low)
        (pl.col("HIGH") - pl.col("LOW")).rolling_mean(window_size=14).fill_null(0.001).alias("ATR"),
        # Volatility/ADX Proxy (14-period standard deviation of Close)
        pl.col("CLOSE").rolling_std(window_size=14).fill_null(0.001).alias("ADX"),
        # EMAs
        pl.col("CLOSE").ewm_mean(span=9, adjust=False).alias("EMA_9"),
        pl.col("CLOSE").ewm_mean(span=21, adjust=False).alias("EMA_21"),
        pl.col("CLOSE").ewm_mean(span=50, adjust=False).alias("EMA_50"),
        pl.col("CLOSE").ewm_mean(span=200, adjust=False).alias("EMA_200")
    ])

    # 3. Convert to strict 1D Float32 NumPy arrays for the PPO Engine (SPEED HACK #3)
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
    Includes spread, commissions, and simulated slippage.
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
        
        # Instantly load from RAM cache
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
        
        # 1. OHLC Window
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
        
        # 3. Giant Radar (8 metrics: ATR, ADX, EMAs, Spread)
        radar = np.array([
            self.data["ATR"][self.current_step],
            self.data["ADX"][self.current_step],
            self.data["EMA_9"][self.current_step],
            self.data["EMA_21"][self.current_step],
            self.data["EMA_50"][self.current_step],
            self.data["EMA_200"][self.current_step],
            self.data["SPREAD"][self.current_step],
            0.0 # Placeholder for future custom metric
        ], dtype=np.float32)
        
        # 4. Strategy Votes (14 robots - simulating neutral votes for now)
        votes = np.zeros(14, dtype=np.float32)
        
        # 5. Glue together into a single 1D float32 array
        return np.concatenate((window, state, radar, votes)).astype(np.float32)

    def step(self, action):
        current_price = self.data["CLOSE"][self.current_step]
        current_spread = self.data["SPREAD"][self.current_step]
        
        reward = 0.0
        
        # Map Action: 0->0, 1->1, 2->-1
        desired_position = 0 if action == 0 else (1 if action == 1 else -1)
        
        # --- EXECUTE TRADE LOGIC ---
        if desired_position != self.position:
            # 1. Close existing position if any
            if self.position == 1:
                pnl = (current_price - self.entry_price) * self.lot_size
                self.balance += pnl
            elif self.position == -1:
                pnl = (self.entry_price - current_price) * self.lot_size
                self.balance += pnl
                
            # 2. Open new position if requested
            if desired_position != 0:
                spread_cost = current_spread * self.lot_size
                commission_cost = self.commission_per_lot * 2 # In & Out
                slippage_cost = self.slippage_penalty * self.lot_size
                trade_cost = spread_cost + commission_cost + slippage_cost
                
                self.balance -= trade_cost
                
                if desired_position == 1:
                    self.entry_price = current_price + (current_spread / 2) + self.slippage_penalty
                else:
                    self.entry_price = current_price - (current_spread / 2) - self.slippage_penalty
                    
                self.trades_executed += 1
                
            self.position = desired_position

        # --- CALCULATE EQUITY ---
        floating_pnl = 0.0
        if self.position == 1:
            floating_pnl = (current_price - self.entry_price) * self.lot_size
        elif self.position == -1:
            floating_pnl = (self.entry_price - current_price) * self.lot_size
            
        previous_equity = self.equity
        self.equity = self.balance + floating_pnl
        
        # Raw Reward is simply the change in real equity (Profit/Loss)
        reward = self.equity - previous_equity
        
        # Advance Time
        self.current_step += 1
        
        # Check if blown up (< 10% equity) or out of data
        terminated = bool(self.equity <= self.initial_balance * 0.10)
        truncated = bool(self.current_step >= self.max_steps)
        
        return self._get_obs(), float(reward), terminated, truncated, {"equity": self.equity, "trades": self.trades_executed}


class InstitutionalRewardWrapper(gym.RewardWrapper):
    """
    Modifies the raw PnL reward of the gym to force institutional behavior.
    """
    def __init__(self, env):
        super().__init__(env)
        self.equity_history = []
        self.flat_steps = 0
        
    def reward(self, raw_reward):
        self.equity_history.append(self.env.unwrapped.equity)
        if len(self.equity_history) > 100:
            self.equity_history.pop(0)
            
        modified_reward = raw_reward
        
        # Penalize doing nothing for too long
        if self.env.unwrapped.position == 0:
            self.flat_steps += 1
            if self.flat_steps > 24: # Waited too long
                modified_reward -= 0.5 
        else:
            self.flat_steps = 0
            
        # Give a bonus for breaking All-Time-High Equity (High Watermark)
        if len(self.equity_history) == 100 and self.env.unwrapped.equity >= max(self.equity_history):
            modified_reward += 2.0 
            
        return modified_reward / 10.0 # Scale reward down for stable neural network gradients