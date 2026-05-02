import os
import sys
import glob
import json

# [CRITICAL FIX] Inject the AURA Root Directory into Python's path so it can find the 'rl' module
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(BASE_DIR)

from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import SubprocVecEnv
from stable_baselines3.common.callbacks import CheckpointCallback

from rl.environments.HarshSimGym import HarshSimGym
from rl.environments.reward_functions import InstitutionalRewardWrapper

PARQUET_DIR = os.path.join(BASE_DIR, "data", "parquet_capsules")
BRAINS_DIR = os.path.join(BASE_DIR, "rl", "brains")
MODEL_DIR = os.path.join(BASE_DIR, "rl", "models")
LOG_DIR = os.path.join(BASE_DIR, "rl", "training", "tensorboard_logs")

os.makedirs(MODEL_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

# DELETE THIS LINE (Line 15):
# from rl.environments.reward_functions import InstitutionalRewardWrapper

def make_env(parquet_path, rank, seed=0):
    """ Utility function for multiprocess env """
    def _init():
        env = HarshSimGym(parquet_path=parquet_path, window_size=60)
        # DELETE THIS LINE (Line 29): 
        # env = InstitutionalRewardWrapper(env)
        env.reset(seed=seed + rank)
        return env
    return _init
def get_available_symbols():
    """Reads JSON files from rl/brains to find which symbols are ready for training."""
    symbols = []
    if not os.path.exists(BRAINS_DIR):
        return symbols
        
    for f in os.listdir(BRAINS_DIR):
        if f.endswith("_rl_params.json"):
            path = os.path.join(BRAINS_DIR, f)
            try:
                with open(path, 'r') as json_file:
                    data = json.load(json_file)
                    sym = data.get("symbol", f.replace("_rl_params.json", ""))
                    symbols.append((sym, data))
            except:
                continue
    return symbols

if __name__ == "__main__":
    # Lock to 4 CPU cores for fast parallel training without crashing Windows
    num_cpu = 4  
    total_training_steps = 1000000  # 1 Million steps per symbol
    
    symbols_to_train = get_available_symbols()
    
    if not symbols_to_train:
        print("[!] No tuned hyperparameters found. Run Phase 3.5 first.")
        sys.exit(1)
        
    for sym, params in symbols_to_train:
        print(f"\n==================================================")
        print(f" TRAINING FOR {sym}...")
        print(f"==================================================")
        
        # [CRITICAL FIX] Find the lowest timeframe Parquet file, and get the STRING (index [0])
        matching_files = glob.glob(os.path.join(PARQUET_DIR, f"{sym}_*M1*.parquet"))
        if not matching_files:
            matching_files = glob.glob(os.path.join(PARQUET_DIR, f"{sym}_*.parquet"))
            
        if not matching_files:
            print(f"[!] No Parquet data found for {sym}. Skipping.")
            continue
            
        target_file = matching_files[0] # Grab the single string path, not the list!
        
        # Load hyperparameters safely
        ppo_params = params.get("ppo_hyperparameters", {})
        lr = ppo_params.get("learning_rate", 0.0003)
        ent_coef = ppo_params.get("ent_coef", 0.01)
        n_steps = ppo_params.get("n_steps", 2048)
        batch_size = ppo_params.get("batch_size", 64)
        
        try:
            vec_env = SubprocVecEnv([make_env(target_file, i) for i in range(num_cpu)])
            
            # Name format matches what live_inference.py expects: {symbol}_Master_PPO_v1.zip
            model_name = f"{sym}_Master_PPO_v1"
            save_path = os.path.join(MODEL_DIR, model_name)
            
            model = PPO(
                "MlpPolicy", 
                vec_env, 
                learning_rate=lr, 
                ent_coef=ent_coef, 
                n_steps=n_steps, 
                batch_size=batch_size, 
                verbose=1, 
                tensorboard_log=LOG_DIR,
                device="cpu"
            )
            
            # Start Training!
            model.learn(total_timesteps=total_training_steps, tb_log_name=f"PPO_{sym}")
            
            # Save the final model
            model.save(save_path)
            print(f"\n[OK] Model saved successfully: {save_path}.zip")
            
            # Close the vectorized environments before moving to the next symbol
            vec_env.close()
            
        except Exception as e:
            print(f"\n[!] Training failed for {sym}: {e}")

    print("\n[AURA] All queued symbols processed.")