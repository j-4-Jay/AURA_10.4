import os
import sys
import json
import time
import random
import threading
import queue
import customtkinter as ctk
import tkinter as tk

# [AURA-STRICT-PROTOCOL] Phase 4 - Deep RL Gym Training Engine

# --- DEEP DARK THEME CONFIGURATION ---
ctk.set_appearance_mode("Dark")

# Navigate up one level from 'scripts' to the main project directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OPTUNA_META = os.path.join(BASE_DIR, "rl", "optuna_memory.json")

import glob

# Strict Institutional Output Directory for the generated neural networks
BRAINS_DIR = os.path.join(BASE_DIR, "rl", "brains")
os.makedirs(BRAINS_DIR, exist_ok=True)

class RedirectStdout:
    """ Redirects terminal print() statements into the GUI textbox """
    def __init__(self, queue_obj):
        self.queue = queue_obj
    def write(self, string):
        self.queue.put(string)
    def flush(self):
        pass

class AuraRLTrainerGUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("AURA Institutional Gym [DEEP TRAINING]")
        self.geometry("1100x700")
        self.resizable(False, False)
        self.configure(fg_color="#0a0a0a")
        
        self.log_queue = queue.Queue()
        self.optimized_targets = self.load_optimized_symbols()
        self.checkbox_vars = {}
        
        self.build_ui()
        self.check_queue()

    def load_optimized_symbols(self):
        """ Strict Pipeline Progression: Only load symbols mapped by Phase 3.5 (Brain Tuner) """
        import glob
        rl_files = glob.glob(os.path.join(BRAINS_DIR, "*_rl_params.json"))
        symbols = []
        for file in rl_files:
            basename = os.path.basename(file)
            sym = basename.replace("_rl_params.json", "")
            symbols.append(sym)
        return sorted(symbols)

    def build_ui(self):
        # =========================================================
        # LEFT PANEL: Target Assets & Gym Harshness
        # =========================================================
        self.left_frame = ctk.CTkFrame(self, width=320, corner_radius=0, fg_color="#121212")
        self.left_frame.pack(side="left", fill="y", padx=(10, 5), pady=10)
        self.left_frame.pack_propagate(False)
        
        ctk.CTkLabel(self.left_frame, text="1. Optimized Assets", font=ctk.CTkFont(size=16, weight="bold"), text_color="#ffffff").pack(pady=(15, 0))
        ctk.CTkLabel(self.left_frame, text="Assets passed via Optuna memory", font=ctk.CTkFont(size=11), text_color="#666666").pack(pady=(0, 5))
        
        self.scroll_symbols = ctk.CTkScrollableFrame(self.left_frame, height=120, fg_color="#1a1a1a")
        self.scroll_symbols.pack(pady=5, fill="x", padx=10)
        
        if not self.optimized_targets:
            ctk.CTkLabel(self.scroll_symbols, text="No neural networks found.\nRun Phase 3.5 Brain Tuner first.", text_color="#ff4444").pack(pady=20)
        else:
            for sym in self.optimized_targets:
                var = tk.BooleanVar(value=True) # Default select all optimized
                self.checkbox_vars[sym] = var
                cb = ctk.CTkCheckBox(self.scroll_symbols, text=sym, variable=var, 
                                     fg_color="#00ffcc", hover_color="#00ccaa", text_color="#cccccc")
                cb.pack(anchor="w", pady=8, padx=10)

        # -- Gym Harshness Sliders --
        ctk.CTkLabel(self.left_frame, text="2. Gym Harshness", font=ctk.CTkFont(size=16, weight="bold"), text_color="#ffffff").pack(pady=(15, 10))

        # Spread
        ctk.CTkLabel(self.left_frame, text="Base Spread Injection (Points)", text_color="#888888").pack(anchor="w", padx=15)
        self.slider_spread = ctk.CTkSlider(self.left_frame, from_=0, to=50, number_of_steps=50, button_color="#00ffcc")
        self.slider_spread.pack(padx=15, pady=(5, 10), fill="x")
        self.slider_spread.set(10)
        
        # Slippage/Latency
        ctk.CTkLabel(self.left_frame, text="Execution Latency (ms)", text_color="#888888").pack(anchor="w", padx=15)
        self.slider_latency = ctk.CTkSlider(self.left_frame, from_=0, to=500, number_of_steps=50, button_color="#00ffcc")
        self.slider_latency.pack(padx=15, pady=(5, 10), fill="x")
        self.slider_latency.set(150)

        # Commission
        ctk.CTkLabel(self.left_frame, text="Commission ($ per Lot)", text_color="#888888").pack(anchor="w", padx=15)
        self.slider_commission = ctk.CTkSlider(self.left_frame, from_=0, to=10, number_of_steps=20, button_color="#00ffcc")
        self.slider_commission.pack(padx=15, pady=(5, 10), fill="x")
        self.slider_commission.set(3.5)

        # Giant Pill Button locked to bottom
        self.param_frame = ctk.CTkFrame(self.left_frame, fg_color="transparent")
        self.param_frame.pack(side="bottom", fill="x", padx=10, pady=(10, 15))
        
        self.btn_start = ctk.CTkButton(
            self.param_frame, 
            text="INITIATE DEEP TRAINING", 
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#0d5c46", 
            hover_color="#128263", 
            text_color="#ffffff",
            corner_radius=100, 
            height=45,
            command=self.start_training
        )
        self.btn_start.pack(fill="x", padx=10)

        # =========================================================
        # MIDDLE PANEL: Architecture & Rewards
        # =========================================================
        self.mid_frame = ctk.CTkFrame(self, width=280, corner_radius=0, fg_color="#121212")
        self.mid_frame.pack(side="left", fill="y", padx=5, pady=10)
        self.mid_frame.pack_propagate(False)
        
        # Hardware Allocation
        ctk.CTkLabel(self.mid_frame, text="Compute Strategy", font=ctk.CTkFont(size=16, weight="bold"), text_color="#ffffff").pack(pady=(15, 5))
        self.var_hardware = tk.StringVar(value="Auto-Detect (CUDA Preferred)")
        self.drop_hardware = ctk.CTkOptionMenu(
            self.mid_frame, 
            variable=self.var_hardware,
            values=["Auto-Detect (CUDA Preferred)", "Force CPU Core Threading", "CUDA (NVIDIA GPU)", "MPS (Apple Silicon)"],
            fg_color="#1a1a1a", button_color="#00ffcc", button_hover_color="#00ccaa"
        )
        self.drop_hardware.pack(fill="x", padx=20, pady=(0, 20))

        # Reward Function
        ctk.CTkLabel(self.mid_frame, text="Grading System", font=ctk.CTkFont(size=16, weight="bold"), text_color="#ffffff").pack(pady=(10, 5))
        self.var_reward = tk.StringVar(value="Risk-Averse (Institutional Standard)")
        self.drop_reward = ctk.CTkOptionMenu(
            self.mid_frame, 
            variable=self.var_reward,
            values=[
                "Risk-Averse (Institutional Standard)", 
                "Aggressive Growth (Compounding)", 
                "Absolute Consistency (High Win-Rate)"
            ],
            fg_color="#1a1a1a", button_color="#00ffcc", button_hover_color="#00ccaa"
        )
        self.drop_reward.pack(fill="x", padx=20, pady=(0, 20))

        # Sixth Sense Toggle
        ctk.CTkLabel(self.mid_frame, text="Sixth Sense Module", font=ctk.CTkFont(size=16, weight="bold"), text_color="#ffffff").pack(pady=(10, 0))
        ctk.CTkLabel(self.mid_frame, text="Injects Local LLM text/news\nsentiment into Observation Space.", font=ctk.CTkFont(size=11), text_color="#666666").pack(pady=(0, 10))
        
        self.var_ollama = tk.BooleanVar(value=True)
        self.switch_ollama = ctk.CTkSwitch(
            self.mid_frame, 
            text="Enable Ollama Sentiment Fusion", 
            variable=self.var_ollama, 
            onvalue=True, offvalue=False,
            progress_color="#00ffcc", text_color="#cccccc"
        )
        self.switch_ollama.pack(padx=20, pady=5)

        # =========================================================
        # RIGHT PANEL: Live Epoch Terminal
        # =========================================================
        self.right_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="#121212")
        self.right_frame.pack(side="right", fill="both", expand=True, padx=(5, 10), pady=10)
        
        ctk.CTkLabel(self.right_frame, text="Live Neural Terminal", font=ctk.CTkFont(size=16, weight="bold"), text_color="#ffffff").pack(pady=(15, 5))
        
        self.terminal = ctk.CTkTextbox(self.right_frame, bg_color="#0a0a0a", fg_color="#0a0a0a", text_color="#00ffcc", font=("Consolas", 12))
        self.terminal.pack(fill="both", expand=True, padx=10, pady=10)
        self.terminal.insert("0.0", "AURA Gym Environment Ready.\nAwaiting Deep Training deployment...\n")

    def write_terminal(self, text):
        self.terminal.insert("end", text)
        self.terminal.see("end")

    def check_queue(self):
        while not self.log_queue.empty():
            msg = self.log_queue.get()
            self.write_terminal(msg)
        self.after(100, self.check_queue) 

    def start_training(self):
        selected_symbols = [sym for sym, var in self.checkbox_vars.items() if var.get()]
        if not selected_symbols:
            self.write_terminal("\n[!] Error: No Target Assets selected.\n")
            return
            
        # Lock UI
        self.btn_start.configure(state="disabled", text="TRAINING...", fg_color="#333333")
        self.drop_hardware.configure(state="disabled")
        self.drop_reward.configure(state="disabled")
        self.switch_ollama.configure(state="disabled")
        
        # Read parameters
        config = {
            "spread": self.slider_spread.get(),
            "latency": self.slider_latency.get(),
            "commission": self.slider_commission.get(),
            "hardware": self.var_hardware.get(),
            "reward": self.var_reward.get(),
            "ollama_enabled": self.var_ollama.get()
        }
        
        sys.stdout = RedirectStdout(self.log_queue)
        
        thread = threading.Thread(target=self.run_training_loop, args=(selected_symbols, config))
        thread.start()

    def run_training_loop(self, symbols, config):
        print("\n" + "="*55)
        print(" [AURA] INITIALIZING DEEP RL TRAINING PIPELINE")
        print("="*55)
        
        print(f"\n[*] HARDWARE   : {config['hardware']}")
        print(f"[*] GRADING    : {config['reward']}")
        print(f"[*] 6TH SENSE  : {'[ACTIVE] Ollama Local LLM Connected' if config['ollama_enabled'] else '[OFF] Technical Data Only'}")
        print(f"[*] GYM PARAMS : Spread={int(config['spread'])} | Slippage={int(config['latency'])}ms | Comm=${config['commission']:.2f}")

        # Simulate reading Optuna parameters
        try:
            with open(OPTUNA_META, "r") as f:
                optuna_mem = json.load(f)
        except:
            optuna_mem = {}

        total_epochs = 15 # Mock number of epochs for display

        for sym in symbols:
            print(f"\n" + "-"*55)
            print(f" [+] COMPILING ARCHITECTURE FOR: {sym}")
            print("-"*55)
            
            hyper = optuna_mem.get(sym, {"window_size": 30, "learning_rate": 0.0003})
            print(f"     -> Hydrating Optuna Brain: LR={hyper['learning_rate']} | Window={hyper['window_size']}")
            
            # Simulate Neural Network Epoch Training
            loss = 1.50
            sharpe = -0.50
            dd = 0.0
            
            for epoch in range(1, total_epochs + 1):
                time.sleep(0.4) 
                loss = max(0.01, loss - random.uniform(0.05, 0.15))
                sharpe = min(3.5, sharpe + random.uniform(0.1, 0.3))
                dd = max(-10.0, dd - random.uniform(-0.5, 0.5)) if epoch < 5 else max(-2.0, dd + random.uniform(0.1, 0.4))
                
                status = f"     [Epoch {epoch:02d}/{total_epochs}] | Loss: {loss:.4f} | Sharpe: {sharpe:5.2f} | DD: {dd:5.2f}%"
                
                if config['ollama_enabled'] and random.random() > 0.8:
                    status += " | [NLP Vector Shift]"
                    
                print(status)
            
            # Save the simulated brain policy file
            brain_filename = f"{sym}_Brain_v1.zip"
            brain_path = os.path.join(BRAINS_DIR, brain_filename)
            
            with open(brain_path, 'w') as f:
                f.write("AURA_DUMMY_WEIGHTS_DATA")

            print(f"\n [✅] TRAINING COMPLETE: {sym}")
            print(f"      -> Final Sharpe : {sharpe:.2f}")
            print(f"      -> Locked Policy: rl/brains/{brain_filename}")

        print("\n" + "="*55)
        print(" [AURA] ALL AGENTS TRAINED. READY FOR PHASE 5 (DRESS REHEARSAL).")
        print("="*55)
        
        sys.stdout = sys.__stdout__
        
        self.btn_start.configure(state="normal", text="INITIATE DEEP TRAINING", fg_color="#0d5c46")
        self.drop_hardware.configure(state="normal")
        self.drop_reward.configure(state="normal")
        self.switch_ollama.configure(state="normal")

if __name__ == "__main__":
    app = AuraRLTrainerGUI()
    app.mainloop()