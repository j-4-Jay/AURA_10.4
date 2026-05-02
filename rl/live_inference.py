import os
import time
import requests
import numpy as np
from stable_baselines3 import PPO
import sys
from colorama import init, Fore, Style
import warnings
warnings.filterwarnings("ignore", category=FutureWarning)

init(autoreset=True)

# [AURA-STRICT-PROTOCOL] Phase 7 - Live Trading Engine
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_DIR = os.path.join(BASE_DIR, "rl", "models")
FASTAPI_URL = "http://127.0.0.1:8000/api/v1/"

class AuraLiveInference:
    def __init__(self, symbol="EURUSDm", model_version="v1"):
        self.symbol = symbol
        self.window_size = 60
        self.tick_buffer = [] 
        
        print(f"{Fore.CYAN}[AURA BRAIN] Initializing Neural Cortex for {self.symbol}...{Style.RESET_ALL}")
        
        # Load the trained weights
        model_path = os.path.join(MODEL_DIR, f"{self.symbol}_Master_PPO_{model_version}.zip")
        if not os.path.exists(model_path):
            print(f"{Fore.YELLOW}[WARNING] Neural weights not found at {model_path}.{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}[WARNING] AI will generate RANDOM actions for testing!{Style.RESET_ALL}")
            self.model = None
        else:
            print(f"{Fore.GREEN}[OK] Loaded Neural Weights: {os.path.basename(model_path)}{Style.RESET_ALL}")
            self.model = PPO.load(model_path, device="cpu")
            
        self.current_position = 0 
        self.floating_pnl_pct = 0.0

    def fetch_live_market_state(self):
        """Poll the FastAPI backend for the latest payload sent by MT5."""
        try:
            res = requests.get(f"{FASTAPI_URL}status/{self.symbol}", timeout=2)
            if res.status_code == 200:
                return res.json()
            return None
        except requests.exceptions.ConnectionError:
            print(f"{Fore.RED}[!] Backend offline. Waiting for Boot Commander...{Style.RESET_ALL}")
            return None
        except Exception:
            return None

    def build_observation_matrix(self, mt5_json):
        """Reconstructs the 264-feature array for the Neural Network"""
        current_price = mt5_json.get('bid', 0.0)
        
        # 1. Manage the OHLC Buffer (Simulated from ticks)
        if len(self.tick_buffer) == 0:
            self.tick_buffer = [current_price] * self.window_size
        else:
            self.tick_buffer.append(current_price)
            if len(self.tick_buffer) > self.window_size:
                self.tick_buffer.pop(0)
                
        window = []
        for p in self.tick_buffer:
            window.extend([p, p + 0.0001, p - 0.0001, p]) # Simulating OHLC
            
        obs_window = np.array(window, dtype=np.float32)
        
        # 2. Extract State
        state = np.array([self.current_position, self.floating_pnl_pct], dtype=np.float32)
        
        # 3. Extract Radar (8 features)
        radar_data = mt5_json.get('radar', {})
        radar_arr = np.array([
            mt5_json.get('atr', 0.0), 
            mt5_json.get('adx', 0.0),
            radar_data.get('dist_vwap', 0.0),
            radar_data.get('dist_liq_h', 0.0),
            radar_data.get('dist_liq_l', 0.0),
            radar_data.get('pd_zone', 0.0),
            radar_data.get('dist_ob_bull', 0.0),
            radar_data.get('dist_ob_bear', 0.0)
        ], dtype=np.float32)
        
        # 4. Extract 14 Robot Votes
        votes_data = mt5_json.get('strategy_votes', [0]*14)
        votes_arr = np.array(votes_data, dtype=np.float32)
        
        # 5. Glue together
        return np.concatenate([obs_window, state, radar_arr, votes_arr])

    def dispatch_signal(self, action_int):
        action_map = {0: "CLOSE", 1: "BUY", 2: "SELL"}
        command = action_map.get(action_int, "NONE")
        
        if command == "CLOSE" and self.current_position == 0:
            return 
            
        if command != "NONE":
            try:
                res = requests.post(f"{FASTAPI_URL}rl_signal?symbol={self.symbol}&action={command}", timeout=2)
                if res.status_code == 200:
                    color = Fore.GREEN if command == "BUY" else Fore.RED if command == "SELL" else Fore.YELLOW
                    print(f"{color}[AURA EXECUTION] Dispatched: {command} on {self.symbol}{Style.RESET_ALL}")
                    if command == "BUY": self.current_position = 1
                    elif command == "SELL": self.current_position = -1
                    elif command == "CLOSE": self.current_position = 0
            except Exception as e:
                print(f"{Fore.RED}[!] Failed to dispatch signal to Backend: {e}{Style.RESET_ALL}")

    def run_dress_rehearsal(self):
        print(f"{Fore.MAGENTA}[*] AI Engine engaged. Waiting for MT5 ticks...{Style.RESET_ALL}")
        try:
            while True:
                # 1. Ask FastAPI for the latest MT5 Data
                mt5_data = self.fetch_live_market_state()
                
                if mt5_data:
                    # 2. Build Matrix
                    obs = self.build_observation_matrix(mt5_data)
                    
                    # 3. Ask AI
                    if self.model:
                        action, _ = self.model.predict(obs, deterministic=True)
                        action_int = int(action)
                    else:
                        # Fallback for testing if model missing
                        action_int = np.random.choice([0, 1, 2])
                        
                    # 4. Send command
                    self.dispatch_signal(action_int)
                    
                # Sleep briefly to avoid flooding CPU. The AI reacts roughly once per second.
                time.sleep(1.0)
                
        except KeyboardInterrupt:
            print(f"\n{Fore.MAGENTA}[AURA BRAIN] Engine disengaged. Sleeping.{Style.RESET_ALL}")

if __name__ == "__main__":
    # For Phase 7, we test EURUSDm by default.
    # Note: Ensure the model filename matches what is in your rl/models/ folder!
    brain = AuraLiveInference(symbol="EURUSDm", model_version="v1")
    brain.run_dress_rehearsal()