import os
import time
import requests
import numpy as np
from stable_baselines3 import PPO
import feedparser
import sys

# sys.path.append(...)  # Keep your sys.path if you need it
# from agents.sentiment_ollama_agent import SentimentOllamaAgent

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_DIR = os.path.join(BASE_DIR, "rl", "models")
FASTAPI_URL = "http://127.0.0.1:8000/api/v1/"

class AuraLiveInference:
    def __init__(self, symbol="EURUSDm", model_version="v2"):
        self.symbol = symbol
        self.window_size = 60
        self.tick_buffer = [] 
        
        model_path = os.path.join(MODEL_DIR, f"{self.symbol}_MasterPPO_{model_version}.zip")
        if not os.path.exists(model_path):
            print(f"[WARNING] Model not found at {model_path}. Using placeholder weights.")
            # self.model = PPO.load(model_path, device="cpu")
        else:
            print(f"[AURA] Loading Neural Weights from {os.path.basename(model_path)}")
            self.model = PPO.load(model_path, device="cpu")
            
        # self.sentiment_agent = SentimentOllamaAgent(model_name="llama3")
        self.current_position = 0 
        self.floating_pnl_pct = 0.0

    def fetch_live_market_state(self):
        """Poll the FastAPI backend for the latest payload sent by MT5."""
        try:
            # We assume your FastAPI has an endpoint that stores the latest MT5 JSON
            res = requests.get(f"{FASTAPI_URL}status/{self.symbol}")
            if res.status_code == 200:
                return res.json() # Returns the full MT5 payload
            return None
        except Exception as e:
            print(f"[!] Backend disconnected: {e}")
            return None

    def build_observation_matrix(self, mt5_json):
        """
        Reconstructs the EXACT 264-feature array the model expects:
        60 candles * 4 + 2 state features + 8 radar features + 14 strategy votes
        """
        current_price = mt5_json.get('bid', 0.0)
        
        # 1. Manage the OHLC Buffer
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
        
        # 5. Glue together in exact order: [OHLC, State, Radar, Votes]
        return np.concatenate([obs_window, state, radar_arr, votes_arr])

    def dispatch_signal(self, action_int):
        action_map = {0: "CLOSE", 1: "BUY", 2: "SELL"}
        command = action_map.get(action_int, "NONE")
        
        if command == "CLOSE" and self.current_position == 0:
            return 
            
        if command != "NONE":
            try:
                res = requests.post(f"{FASTAPI_URL}rl_signal?symbol={self.symbol}&action={command}")
                if res.status_code == 200:
                    print(f"[AURA EXECUTION] - Dispatched command: {command}")
                    if command == "BUY": self.current_position = 1
                    elif command == "SELL": self.current_position = -1
                    elif command == "CLOSE": self.current_position = 0
            except Exception as e:
                print(f"[!] Failed to dispatch signal: {e}")

    def run_dress_rehearsal(self):
        print(f"[AURA] Initiating Live Inference for {self.symbol}...")
        try:
            while True:
                # 1. Ask FastAPI for the latest Radar Data from MT5
                mt5_data = self.fetch_live_market_state()
                
                if mt5_data:
                    # 2. Build the Massive Matrix
                    obs = self.build_observation_matrix(mt5_data)
                    
                    # 3. Ask the AI Captain
                    if hasattr(self, 'model'):
                        action, _states = self.model.predict(obs, deterministic=True)
                        action_int = int(action)
                    else:
                        action_int = 0 # Fallback if model didn't load
                        
                    if action_int != 0:
                        print("Technical signal triggered.")
                        # Add your Sentiment override logic back here if needed!
                        self.dispatch_signal(action_int)
                        
                time.sleep(1) # Poll every 1 second
                
        except KeyboardInterrupt:
            print("\n[AURA] Inference Terminated.")

if __name__ == "__main__":
    engine = AuraLiveInference(symbol="EURUSDm", model_version="v2")
    engine.run_dress_rehearsal()