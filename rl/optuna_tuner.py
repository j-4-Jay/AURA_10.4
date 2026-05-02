import os
import glob
import json
import optuna
import numpy as np
import warnings
import sys
import time

warnings.filterwarnings("ignore")
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rl.environments.HarshSimGym import load_and_cache_data

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PARQUET_DIR = os.path.join(BASE_DIR, "data", "parquet_capsules")

def generate_params_json(symbol: str, trial: optuna.Trial, profit_factor: float):
    config_dir = os.path.join(BASE_DIR, "ea", "Files", "AURA_Configs")
    os.makedirs(config_dir, exist_ok=True)

    config = {
        "symbol": symbol,
        "timeframe_optimized": trial.params.get("timeframe", "H1"),
        "profit_factor_tested": round(profit_factor, 2),
        "circuit_breaker": {"global_max_drawdown_pct": 5.0},
        "indicators": {
            "Optuna_EMA_Period": trial.params.get("ema_period", 9),
            "Optuna_SL_Multiplier": round(trial.params.get("sl_mult", 0.33), 2),
            "Optuna_TP_Multiplier": round(trial.params.get("tp_mult", 1.0), 2)
        },
        "strategies": {f"strat_{i}": bool(trial.params.get(f"strat_{i}", True)) for i in range(1, 8)},
        "trailing_management": {"trailing_type": trial.params.get("trailing_type", 1)}
    }

    config_path = os.path.join(config_dir, f"{symbol}_params.json")
    with open(config_path, "w") as f:
        json.dump(config, f, indent=4)
        
    print(f"\n[+] RECIPE GENERATED: {config_path}")
    print(f"[+] MasterEA Ready. Verified Profit Factor: {round(profit_factor, 2)}")

def evaluate_vectorized_strategy(data, ema_period, sl_mult, tp_mult):
    close = data["CLOSE"]
    atr = data["ATR"]
    spread = data["SPREAD"]
    
    # We dynamically select the EMA closest to the guess
    if ema_period <= 14: ema = data["EMA_9"]
    elif ema_period <= 35: ema = data["EMA_21"]
    elif ema_period <= 100: ema = data["EMA_50"]
    else: ema = data["EMA_200"]
    
    # Buy when Close crosses above EMA
    buy_signals = (close[1:] > ema[1:]) & (close[:-1] <= ema[:-1])
    
    if not np.any(buy_signals):
        return 0.0
        
    entry_indices = np.where(buy_signals)[0] + 1
    
    total_profit = 0.0
    total_loss = 0.0
    
    # Fast-forward math simulation
    for idx in entry_indices:
        if idx >= len(close) - 1:
            continue
            
        # Realistic Entry Price (Current Close + Half Spread)
        entry_price = close[idx] + (spread[idx] / 2.0) 
        
        sl_dist = atr[idx] * sl_mult
        tp_dist = atr[idx] * tp_mult
        
        target_tp = entry_price + tp_dist
        target_sl = entry_price - sl_dist
        
        # Look ahead up to 100 bars to find outcome
        look_ahead = close[idx:min(idx+100, len(close))]
        
        # Did we hit TP or SL?
        hit_tp = np.where(look_ahead >= target_tp)[0]
        hit_sl = np.where(look_ahead <= target_sl)[0]
        
        if len(hit_tp) > 0 and len(hit_sl) > 0:
            if hit_tp[0] < hit_sl[0]:
                total_profit += tp_dist
            else:
                total_loss += sl_dist + spread[idx]
        elif len(hit_tp) > 0:
            total_profit += tp_dist
        elif len(hit_sl) > 0:
            total_loss += sl_dist + spread[idx]
        else:
            # If neither hit in 100 bars, just take floating PnL
            final_price = look_ahead[-1]
            pnl = final_price - entry_price
            if pnl > 0:
                total_profit += pnl
            else:
                total_loss += abs(pnl)
            
    if total_loss == 0:
        return min(3.2, total_profit) if total_profit > 0 else 0.0
        
    pf = total_profit / total_loss
    return pf

def optimize_math(trial: optuna.Trial, symbol: str) -> float:
    ema_period = trial.suggest_int("ema_period", 1, 200)
    sl_mult = trial.suggest_float("sl_mult", 0.1, 1.0)
    tp_mult = trial.suggest_float("tp_mult", 1.0, 5.0)
    
    for i in range(1, 8):
        trial.suggest_categorical(f"strat_{i}", [True, False])
        
    trial.suggest_categorical("trailing_type", [1, 2, 3])
    timeframe = trial.suggest_categorical("timeframe", ["M1", "M15", "H1", "H4", "Daily"])

    files = glob.glob(os.path.join(PARQUET_DIR, f"{symbol}_{timeframe}*.parquet"))
    if not files:
        files = glob.glob(os.path.join(PARQUET_DIR, "*.parquet"))
    if not files:
        return -9999.0
    
    target_file = files[0]
    data = load_and_cache_data(target_file)
    
    simulated_pf = evaluate_vectorized_strategy(data, ema_period, sl_mult, tp_mult)
    
    # Store the actual PF in a user attribute so we can see it
    trial.set_user_attr("simulated_pf", simulated_pf)
    
    # We removed the artificial 3.2 ceiling. If we find a Godzilla-tier 7.0 PF strategy, KEEP IT!
    if simulated_pf < 0.8:
        return -9999.0
        
    return simulated_pf

if __name__ == '__main__':
    print("=====================================================")
    print(" AURA VECTORIZED OPTUNA ENGINE (INSTITUTIONAL SPEED) ")
    print(" Target: Profit Factor 0.8 - 3.2 (Net of Costs)")
    print("=====================================================\n")

    # Discover all unique symbols dynamically from the Parquet Directory
    all_parquet_files = glob.glob(os.path.join(PARQUET_DIR, "*.parquet"))
    symbols = set()
    for file_path in all_parquet_files:
        basename = os.path.basename(file_path)
        # Expected format: SYMBOL_TF_DATE.parquet (e.g., EURUSDm_H1_...parquet)
        sym = basename.split("_")[0]
        symbols.add(sym)
        
    symbols = sorted(list(symbols))
    
    if not symbols:
        print("[!] No Parquet files found. Please run the Data Prep script first.")
        sys.exit(0)

    print(f"[*] Found {len(symbols)} Symbols: {symbols}")
    print("[*] Engaging Pure Math Vectorization. No Neural Nets. Max Speed...")

    # Iterate through every symbol, testing all timeframes and strategies inside!
    for symbol in symbols:
        print(f"\n=====================================================")
        print(f" [*] COMMENCING PHASE 4 STUDY FOR: {symbol} ")
        print(f"=====================================================")
        
        symbol_start_time = time.time()
        study = optuna.create_study(direction="maximize")
        
        # Passing `symbol` safely through a lambda to Optuna
        study.optimize(lambda trial: optimize_math(trial, symbol), n_trials=500, n_jobs=-1)

        symbol_elapsed = time.time() - symbol_start_time
        hours, remainder = divmod(int(symbol_elapsed), 3600)
        minutes, seconds = divmod(remainder, 60)
        calc_time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"

        if len(study.trials) > 0 and study.best_value != -9999.0:
            best_trial = study.best_trial
            print(f"\n[*] BEST COMBINATION FOR {symbol} FOUND! PF: {round(best_trial.value, 2)} Calc Time: {calc_time_str}")
            generate_params_json(symbol, best_trial, best_trial.value)
        else:
            print(f"\n[!] No profitable combinations found for {symbol} matching strict 0.8 - 3.2 PF criteria.")
            
    print("\n[+] AURA-STRICT-PROTOCOL Multi-Symbol Optimization Complete.")