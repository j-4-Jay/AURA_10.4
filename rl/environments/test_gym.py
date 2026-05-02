import os
import glob
from HarshSimGym import HarshSimGym

# [AURA-STRICT-PROTOCOL] Phase 2 Module 3 - The Random Gambler Test
def test_harsh_environment():
    # Automatically find the first Parquet file in the capsules folder
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    parquet_folder = os.path.join(base_dir, "data", "parquet_capsules")
    
    files = glob.glob(os.path.join(parquet_folder, "*.parquet"))
    if not files:
        print("[!] No parquet files found. Run the data pipeline first.")
        return
        
    target_file = files[0] # Grab the first one (e.g., BTC or EURUSD M15)
    
    # Initialize the Environment
    env = HarshSimGym(parquet_path=target_file)
    obs, info = env.reset()
    
    print(f"\n[AURA] Initializing Random Gambler in HarshSimGym...")
    print(f"Starting Balance: ${env.initial_balance:.2f}")
    
    terminated = False
    truncated = False
    step_count = 0
    
    while not (terminated or truncated):
        # Agent takes a totally random action (0, 1, or 2)
        action = env.action_space.sample() 
        
        obs, reward, terminated, truncated, info = env.step(action)
        step_count += 1
        
        if step_count % 1000 == 0:
            print(f"Step {step_count:05d} | Trades: {info['trades']:04d} | Equity: ${info['equity']:,.2f}")
            
    print("\n[AURA] Episode Finished.")
    print(f"Total Steps Survived: {step_count}")
    print(f"Total Trades Executed: {info['trades']}")
    print(f"Final Equity: ${info['equity']:,.2f}")
    
    if terminated:
        print("[RESULT] The agent suffered a Margin Call (Ruin Condition met). The environment is properly harsh.")
    else:
        print("[RESULT] The agent survived until the end of the dataset. Consider increasing transaction costs.")

if __name__ == "__main__":
    test_harsh_environment()