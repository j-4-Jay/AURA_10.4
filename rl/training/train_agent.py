import os
import glob
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv
from stable_baselines3.common.monitor import Monitor
from stable_baselines3.common.callbacks import BaseCallback

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from environments.HarshSimGym import HarshSimGym, InstitutionalRewardWrapper

# [AURA-STRICT-PROTOCOL] Phase 5 - Deep Training with Grading System
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PARQUET_DIR = os.path.join(BASE_DIR, "data", "parquet_capsules")
MODEL_DIR = os.path.join(BASE_DIR, "rl", "models")
TENSORBOARD_LOG = os.path.join(BASE_DIR, "rl", "training", "tensorboard_logs")

os.makedirs(MODEL_DIR, exist_ok=True)
os.makedirs(TENSORBOARD_LOG, exist_ok=True)

class AuraInstitutionalCallback(BaseCallback):
    def __init__(self, verbose=0):
        super(AuraInstitutionalCallback, self).__init__(verbose)
        self.best_equity = 0.0

    def _on_step(self) -> bool:
        env = self.training_env.envs[0].env.unwrapped
        
        if self.num_timesteps % 5000 == 0:
            equity = env.equity
            trades = env.trades_executed
            
            self.logger.record("aura/equity", equity)
            self.logger.record("aura/total_trades", trades)
            
            if equity > self.best_equity:
                self.best_equity = equity
                
            drawdown = ((self.best_equity - equity) / self.best_equity) * 100 if self.best_equity > 0 else 0
            self.logger.record("aura/drawdown_pct", drawdown)
            
        return True

def train_institutional_model(symbol="EURUSDm", time_steps=1_000_000):
    print(f"[AURA] Initializing Institutional RL Training for {symbol}...")
    
    files = glob.glob(os.path.join(PARQUET_DIR, f"{symbol}*H1*.parquet"))
    if not files:
        print("[!] No H1 Parquet data found.")
        return
        
    target_file = files[0]
    print(f"[*] Training on dataset: {os.path.basename(target_file)}")
    
    # 1. Instantiate Gym with Optuna's best window_size
    env = HarshSimGym(parquet_path=target_file, initial_balance=10000.0, lot_size=10000, window_size=60)
    
    # 2. Wrap it in the Grading System
    env = InstitutionalRewardWrapper(env)
    
    # 3. Monitor and Vectorize
    env = Monitor(env)
    vec_env = DummyVecEnv([lambda: env])
    
    # 4. Initialize PPO with Optuna's best hyperparameters
    model = PPO(
        "MlpPolicy", 
        vec_env, 
        learning_rate=0.0008589842199966906, # From Optuna
        ent_coef=0.012492798660829528,       # From Optuna
        n_steps=2048,
        batch_size=64,
        n_epochs=10,
        gamma=0.99,
        max_grad_norm=0.5,
        tensorboard_log=TENSORBOARD_LOG,
        verbose=1,
        device="cpu"
    )
    
    print(f"[*] Commencing Deep Training ({time_steps} timesteps)...")
    callback = AuraInstitutionalCallback()
    
    try:
        model.learn(total_timesteps=time_steps, callback=callback, tb_log_name=f"PPO_{symbol}_Graded")
    except KeyboardInterrupt:
        print("\n[!] Training manually interrupted. Saving current progress...")
        
    model_name = f"{symbol}_Master_PPO_v2"
    save_path = os.path.join(MODEL_DIR, model_name)
    model.save(save_path)
    
    # Unwrapped to bypass the Monitor and Wrapper to get raw stats
    unwrapped_env = vec_env.envs[0].env.unwrapped
    print(f"\n[AURA-STRICT-PROTOCOL] Model successfully trained and locked at: {save_path}.zip")
    print(f"[*] Final Equity: ${unwrapped_env.equity:,.2f}")
    print(f"[*] Total Trades Executed: {unwrapped_env.trades_executed}")

if __name__ == "__main__":
    train_institutional_model(symbol="EURUSDm", time_steps=50_000)