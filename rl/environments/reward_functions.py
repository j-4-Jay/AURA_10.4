import gymnasium as gym
import numpy as np

class InstitutionalRewardWrapper(gym.RewardWrapper):
    """
    [AURA-STRICT-PROTOCOL]
    This wrapper reshapes the raw PnL reward from HarshSimGym.
    It forces the AI to execute clean, fast sniper trades instead of holding forever.
    """
    def __init__(self, env):
        super().__init__(env)
        self.time_in_trade = 0
        
    def step(self, action):
        observation, reward, terminated, truncated, info = self.env.step(action)
        done = terminated or truncated
        
        # 1. Time Decay Penalty (The longer you hold, the more it hurts)
        # This prevents the "Hold and Pray" behavior.
        current_position = info.get('current_position', 0)
        if current_position != 0:
            self.time_in_trade += 1
            # Penalty scales up the longer they are in the trade
            reward -= (0.0005 * self.time_in_trade)
        else:
            self.time_in_trade = 0
            
        # 2. Inactivity Penalty (Don't just sit there for days doing nothing)
        # If the AI doesn't trade, it slowly bleeds reward.
        if current_position == 0:
            reward -= 0.0001
            
        # 3. Asymmetric Win/Loss Scaling
        # We want to encourage the AI to take calculated risks. 
        # If it closes a winning trade, we amplify the dopamine hit!
        realized_pnl = info.get('realized_pnl', 0.0)
        if realized_pnl > 0:
            reward += (realized_pnl * 1.5)  # 1.5x Multiplier for winning
            
        return observation, self.reward(reward), terminated, truncated, info
        
    def reward(self, reward):
        # Clip reward between -15 and +15 to prevent the neural network 
        # gradients from exploding during massive market spikes
        return np.clip(reward, -15.0, 15.0) 
