import os
import glob
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import SubprocVecEnv
from stable_baselines3.common.callbacks import CheckpointCallback

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from environments.HarshSimGym import HarshSimGym, InstitutionalRewardWrapper

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PARQUET_DIR = os.path.join(BASE_DIR, "data", "parquet_capsules")
MODEL_DIR = os.path.join(BASE_DIR, "rl", "models", "checkpoints")
os.makedirs(MODEL_DIR, exist_ok=True)

def make_env(parquet_path, rank, seed=0):
    """ Utility function for multiprocess env """
    def _init():
        env = HarshSimGym(parquet_path=parquet_path, window_size=60)
        env = InstitutionalRewardWrapper(env)
        env.reset(seed=seed + rank)
        return env
    return _init

if __name__ == "__main__":
    target_file = glob.glob(os.path.join(PARQUET_DIR, "EURUSDm*H1*.parquet"))
    
    # Spin up 4 parallel environments (Adjust based on your CPU cores)
    num_cpu = 4  
    vec_env = SubprocVecEnv([make_env(target_file, i) for i in range(num_cpu)])
    
    # Save a backup of the brain every 100,000 steps so you don't lose progress
    checkpoint_callback = CheckpointCallback(save_freq=max(100_000 // num_cpu, 1), 
                                             save_path=MODEL_DIR, 
                                             name_prefix="EURUSDm_PPO")

    model = PPO("MlpPolicy", vec_env, learning_rate=0.00085, ent_coef=0.012, 
                n_steps=2048, batch_size=256, verbose=1, device="cpu")
    
    print(f"[AURA] Commencing Massive Multi-Core Training (10M Steps)...")
    model.learn(total_timesteps=10_000_000, callback=checkpoint_callback)
    
    model.save(os.path.join(BASE_DIR, "rl", "models", "EURUSDm_Master_PPO_v3"))
    print("[AURA] V3 Institutional Model Locked.")