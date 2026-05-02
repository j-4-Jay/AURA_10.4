import os
import glob
import json
import logging
import warnings
import optuna
import numpy as np
import time

# Suppress annoying TF warnings if using SB3 TF instead of torch, though SB3 is Torch.
import warnings
warnings.filterwarnings("ignore")
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

from stable_baselines3 import PPO
from stable_baselines3.common.evaluation import evaluate_policy

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rl.environments.HarshSimGym import HarshSimGym

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PARQUET_DIR = os.path.join(BASE_DIR, "data", "parquet_capsules")
CONFIG_DIR = os.path.join(BASE_DIR, "ea", "Files", "AURA_Configs")
BRAIN_TUNER_DIR = os.path.join(BASE_DIR, "rl", "brains")
os.makedirs(BRAIN_TUNER_DIR, exist_ok=True)

# To ensure the terminal wrapper parses easily
print("=====================================================")
print(" AURA META-RL BRAIN TUNER (HYPERPARAMETER SWEEP) ")
print(" Tuning Agent Policy: PPO Neural Network ")
print("=====================================================\n")

def objective(trial, symbol, config_path):
    # Load Alpha Edge parameters
    with open(config_path, "r") as f:
        alpha_config = json.load(f)
        
    tf = alpha_config.get("timeframe_optimized", "H1")
    
    # Locate Parquet Data
    files = glob.glob(os.path.join(PARQUET_DIR, f"{symbol}*{tf}*.parquet"))
    if not files:
        files = glob.glob(os.path.join(PARQUET_DIR, f"{symbol}*.parquet"))
        if not files:
            raise FileNotFoundError(f"No parquet data found for {symbol}")
            
    parquet_path = files[0]

    # Suggest Hyperparameters for the PPO Neural Network
    # We lock the baseline and only let Optuna optimize how the brain learns
    n_steps = trial.suggest_categorical("n_steps", [128, 256, 512])
    batch_size = trial.suggest_categorical("batch_size", [32, 64, 128])
    
    # Ensure batch_size is a multiple / divisor of n_steps to prevent PPO crashes
    if batch_size > n_steps:
        batch_size = n_steps
        
    learning_rate = trial.suggest_float("learning_rate", 1e-5, 1e-3, log=True)
    ent_coef = trial.suggest_float("ent_coef", 0.00001, 0.05, log=True)
    gamma = trial.suggest_categorical("gamma", [0.95, 0.98, 0.99, 0.995])
    
    # Initialize Environment
    # Note: We scale window_size down for rapid tuning
    env = HarshSimGym(parquet_path=parquet_path, window_size=30)

    try:
        model = PPO(
            "MlpPolicy",
            env,
            learning_rate=learning_rate,
            n_steps=n_steps,
            batch_size=batch_size,
            ent_coef=ent_coef,
            gamma=gamma,
            verbose=0,
            device="auto"
        )
        
        # Perform a micro-training sweep to evaluate how fast it learns
        # Keep this short so Phase 3.5 stays closer to the speed of Phase 3.
        model.learn(total_timesteps=500, progress_bar=False)
        
        # Evaluate model mechanically 
        mean_reward, std_reward = evaluate_policy(model, env, n_eval_episodes=1, deterministic=True)
        
    except Exception as e:
        # Penalize crashes (like batch size mismatch)
        return -9999.0
        
    return mean_reward

def tune_brain_for_symbol(symbol, config_path):
    print(f"\n[AURA-META] COMMENCING NEURAL SWEEP FOR: {symbol} ...")
    
    symbol_start_time = time.time()
    study = optuna.create_study(direction="maximize")
    # Quick 30 trials per symbol so it runs in a reasonable time. 
    sys.stdout.flush()
    study.optimize(lambda trial: objective(trial, symbol, config_path), n_trials=12, n_jobs=1)
    
    symbol_elapsed = time.time() - symbol_start_time
    hours, remainder = divmod(int(symbol_elapsed), 3600)
    minutes, seconds = divmod(remainder, 60)
    calc_time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    
    best_trial = study.best_trial
    
    print(f"  > {symbol} Brain Tuned! Best Average Validation Reward: {best_trial.value}")
    print(f"BEST NEURAL ARCHITECTURE FOR {symbol} FOUND! Reward: {best_trial.value:.4f} Calc Time: {calc_time_str}")
    sys.stdout.flush()
        
    # Save RL Hyperparameters
    rl_config = {
        "symbol": symbol,
        "best_reward": best_trial.value,
        "ppo_hyperparameters": best_trial.params
    }
    
    out_path = os.path.join(BRAIN_TUNER_DIR, f"{symbol}_rl_params.json")
    with open(out_path, "w") as f:
        json.dump(rl_config, f, indent=4)
        
    print(f"  > [V] Saved Institutional Neural Graph to {out_path}")

if __name__ == "__main__":
    configs = glob.glob(os.path.join(CONFIG_DIR, "*_params.json"))
    if len(configs) == 0:
        print("[!] No baseline configurations found. Please run Alpha Optimization first.")
        sys.exit(1)
        
    for config_path in configs:
        filename = os.path.basename(config_path)
        # Assumes format BTCUSDm_params.json
        sym = filename.replace("_params.json", "")
        
        tune_brain_for_symbol(sym, config_path)
        
    print("\n=====================================================")
    print(" [AURA] STAGE 2 NEURAL TUNING COMPLETE. READY FOR DEEP TRAINING.")
    print("=====================================================")
