import os
import sys
import threading
import json
import subprocess
import time
import datetime
import customtkinter as ctk
import queue
import re

ctk.set_appearance_mode("Dark")

# Exact Hardcoded Master Path
BASE_DIR = r"C:\Users\JAY\Documents\AURA (MT5 Trading)\AURA_10.4"
BRAINS_DIR = os.path.join(BASE_DIR, "rl", "brains")
TRAIN_SCRIPT = os.path.join(BASE_DIR, "rl", "training", "train_multicore.py")

class AuraRLTrainerGUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("AURA Institutional Tuner - PHASE 5 (NEURAL TRAINING)")
        self.geometry("1650x900")
        self.resizable(True, True)
        self.configure(fg_color="#0a0a0a")
        
        self.log_queue = queue.Queue()
        
        self.symbols_dict = {}
        self.hyperparams_paths = {}
        self.scan_available_hyperparams()
        
        self.symbol_title_vars = {}  # Added for dynamic ETA tracking
        self.symbol_status_vars = {}
        self.symbol_progress_vars = {}
        self.symbol_results = {}
        self.symbol_start_times = {}
        
        # Expected epochs/steps per symbol
        self.total_steps = 1000000 

        self.color_palette = ["#00ffcc", "#ff00cc", "#ffcc00", "#00ccff", "#ccff00", "#ff6600", "#cc00ff", "#00ff66"]
        self.symbol_colors = {}
        
        c_index = 0
        for sym in self.symbols_dict.keys():
            self.symbol_colors[sym] = self.color_palette[c_index % len(self.color_palette)]
            c_index += 1

        self.build_ui()
        self.check_queue()

    def scan_available_hyperparams(self):
        """Scans rl/brains for the _rl_params.json files created by Phase 3.5"""
        os.makedirs(BRAINS_DIR, exist_ok=True)
        symbols_map = {}
        
        for f in os.listdir(BRAINS_DIR):
            if f.endswith("_rl_params.json"):
                path = os.path.join(BRAINS_DIR, f)
                try:
                    with open(path, 'r') as json_file:
                        data = json.load(json_file)
                        sym = data.get("symbol", f.replace("_rl_params.json", ""))
                        self.hyperparams_paths[sym] = path
                        
                        ppo = data.get("ppo_hyperparameters", {})
                        n_steps = ppo.get("n_steps", "Unknown")
                        symbols_map[sym] = [f"Steps: {n_steps}"]
                except:
                    pass
                    
        self.symbols_dict = dict(sorted(symbols_map.items()))

    def build_ui(self):
        # LEFT FRAME (Assets)
        self.left_frame = ctk.CTkFrame(self, width=280, corner_radius=0, fg_color="#121212")
        self.left_frame.pack(side="left", fill="y", padx=(10, 5), pady=10)
        self.left_frame.pack_propagate(False)
        
        ctk.CTkLabel(self.left_frame, text="1. Tuned Brains Available", font=ctk.CTkFont(size=16, weight="bold"), text_color="#ffffff").pack(pady=(15, 5))
        
        self.scroll_symbols = ctk.CTkScrollableFrame(self.left_frame, width=240, fg_color="#1a1a1a")
        self.scroll_symbols.pack(pady=5, fill="both", expand=True, padx=10)
        
        if not self.symbols_dict:
            ctk.CTkLabel(self.scroll_symbols, text="No Hyperparameters found. Run Brain Tuner (Phase 3.5).", text_color="#ff4444", wraplength=200).pack(pady=20)
            
        for sym, details in self.symbols_dict.items():
            sym_frame = ctk.CTkFrame(self.scroll_symbols, fg_color="#222222", corner_radius=6)
            sym_frame.pack(fill="x", pady=5, padx=5)
            ctk.CTkLabel(sym_frame, text=f" {sym}", font=ctk.CTkFont(weight="bold"), text_color="#00ccff").pack(anchor="w", padx=10, pady=(5,0))
            tf_str = ", ".join(details)
            ctk.CTkLabel(sym_frame, text=f"Params: {tf_str}", font=ctk.CTkFont(size=11), text_color="#aaaaaa").pack(anchor="w", padx=10, pady=(0,5))
            
        self.btn_start = ctk.CTkButton(
            self.left_frame, text="START GYM TRAINING", font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#0d5c46", hover_color="#128263", text_color="#ffffff", corner_radius=100, height=45,
            command=self.start_optimization
        )
        self.btn_start.pack(pady=(15, 5), fill="x", padx=10)
        
        self.btn_stop = ctk.CTkButton(
            self.left_frame, text="STOP PROCESS", font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#aa0000", hover_color="#ff4444", text_color="#ffffff", corner_radius=100, height=30,
            command=self.stop_optimization, state="disabled"
        )
        self.btn_stop.pack(pady=(0, 15), fill="x", padx=10)

        # MID FRAME (Status)
        self.mid_frame = ctk.CTkFrame(self, width=950, corner_radius=0, fg_color="#121212")
        self.mid_frame.pack(side="left", fill="both", expand=True, padx=0, pady=10)
        self.mid_frame.pack_propagate(False)
        
        ctk.CTkLabel(self.mid_frame, text="2. Live PPO Training Status", font=ctk.CTkFont(size=16, weight="bold"), text_color="#ffffff").pack(pady=(15, 0))
        
        self.scroll_status = ctk.CTkScrollableFrame(self.mid_frame, width=900, fg_color="#1a1a1a")
        self.scroll_status.pack(pady=10, fill="both", expand=True, padx=10)
        
        for sym in self.symbols_dict.keys():
            card = ctk.CTkFrame(self.scroll_status, fg_color="#222222", corner_radius=6)
            card.pack(fill="x", pady=5, padx=5)
            
            header_frame = ctk.CTkFrame(card, fg_color="transparent")
            header_frame.pack(fill="x", padx=10, pady=(5, 0))
            
            # Dynamic Title Variable (Symbol + ETA)
            title_var = ctk.StringVar(value=f"■  {sym}  [ETA: Calculating...]")
            self.symbol_title_vars[sym] = title_var
            ctk.CTkLabel(header_frame, textvariable=title_var, font=ctk.CTkFont(size=14, weight="bold"), text_color="#ffffff").pack(side="left")
            
            status_var = ctk.StringVar(value="Awaiting Gym Initialization...")
            self.symbol_status_vars[sym] = status_var
            ctk.CTkLabel(header_frame, textvariable=status_var, font=ctk.CTkFont(size=11), text_color="#888888").pack(side="right")
            
            prog_var = ctk.DoubleVar(value=0.0)
            self.symbol_progress_vars[sym] = prog_var
            sym_color = self.symbol_colors.get(sym, "#00ffcc")
            
            pb = ctk.CTkProgressBar(card, variable=prog_var, progress_color=sym_color, fg_color="#444444", height=12)
            pb.pack(fill="x", padx=10, pady=(10, 15))

        # RIGHT FRAME (Terminal)
        self.right_frame = ctk.CTkFrame(self, width=380, corner_radius=0, fg_color="#121212")
        self.right_frame.pack(side="right", fill="y", expand=False, padx=(0, 10), pady=10)
        self.right_frame.pack_propagate(False)
        
        ctk.CTkLabel(self.right_frame, text="3. Gym Terminal", font=ctk.CTkFont(size=16, weight="bold"), text_color="#ffffff").pack(pady=(15, 5))
        
        self.terminal = ctk.CTkTextbox(self.right_frame, bg_color="#0a0a0a", fg_color="#0a0a0a", text_color="#00ffcc", font=("Consolas", 12))
        self.terminal.pack(fill="both", expand=True, padx=10, pady=10)
        self.terminal.insert("0.0", "AURA Gym Ready. Start to begin Deep RL PPO Training.\n")

    def write_terminal(self, text, color=None):
        if color:
            tag_name = f"color_{color.replace('#', '')}"
            self.terminal.tag_config(tag_name, foreground=color)
            start_index = self.terminal.index("end-1c")
            self.terminal.insert("end", text + "\n")
            end_index = self.terminal.index("end-1c")
            self.terminal.tag_add(tag_name, start_index, end_index)
        else:
            self.terminal.insert("end", text + "\n")
        self.terminal.see("end")

    def check_queue(self):
        while not self.log_queue.empty():
            item = self.log_queue.get()
            if item == "SUMMARY":
                self.print_optimization_summary()
                continue
                
            if isinstance(item, tuple):
                msg, color = item
                self.write_terminal(msg, color)
                self.parse_subprocess_output(msg)
            else:
                self.write_terminal(item)
                self.parse_subprocess_output(item)
                
        self.after(100, self.check_queue)

    def parse_subprocess_output(self, line):
        # Identify which symbol is currently training
        if "TRAINING" in line and "FOR" in line:
            parts = line.split("FOR")
            if len(parts) > 1:
                sym = parts[1].strip().replace("...", "").strip()
                self.current_optimizing_symbol = sym
                self.symbol_start_times[sym] = time.time()
                if sym in self.symbol_status_vars:
                    self.symbol_status_vars[sym].set("Loading Parquet Data into Gym...")
                    self.symbol_progress_vars[sym].set(0.05)
                    self.symbol_title_vars[sym].set(f"■  {sym}  [ETA: Calculating...]")

        # Parse Tensorboard/PPO Output metrics
        sym = getattr(self, 'current_optimizing_symbol', None)
        if not sym: return

        if "total_timesteps" in line:
            try:
                # Example stable_baselines3 output: | time/total_timesteps | 2048 |
                steps_str = line.split("|")[2].strip()
                steps = int(steps_str)
                prog_val = min(1.0, steps / self.total_steps)
                self.symbol_progress_vars[sym].set(prog_val)
                self.symbol_status_vars[sym].set(f"Training ({steps:,}/{self.total_steps:,} steps)...")
                
                # --- [AURA-STRICT-PROTOCOL] HIGH ACCURACY ETA CALCULATION ---
                start_time = self.symbol_start_times.get(sym, time.time())
                elapsed = time.time() - start_time
                
                # Give it a few seconds to stabilize before calculating
                if elapsed > 5.0 and steps > 0:
                    steps_per_sec = steps / elapsed
                    steps_left = self.total_steps - steps
                    if steps_per_sec > 0:
                        eta_secs = int(steps_left / steps_per_sec)
                        h, rem = divmod(eta_secs, 3600)
                        m, s = divmod(rem, 60)
                        eta_str = f"{h:02d}:{m:02d}:{s:02d}"
                        self.symbol_title_vars[sym].set(f"■  {sym}  [ETA: {eta_str}]")
            except:
                pass
                
        if "ep_rew_mean" in line:
            try:
                rew = line.split("|")[2].strip()
                current_status = self.symbol_status_vars[sym].get()
                if "Reward:" not in current_status:
                    self.symbol_status_vars[sym].set(f"{current_status} | Reward: {rew}")
                else:
                    self.symbol_status_vars[sym].set(re.sub(r'Reward: .*', f'Reward: {rew}', current_status))
            except:
                pass

        if "Model saved" in line or "Training complete" in line:
            self.symbol_results[sym] = "SUCCESS"
            if sym in self.symbol_status_vars:
                self.symbol_status_vars[sym].set("[*] OK | Neural Weights Generated (.zip)")
                self.symbol_progress_vars[sym].set(1.0)
                self.symbol_title_vars[sym].set(f"■  {sym}  [ETA: 00:00:00]")

    def start_optimization(self):
        if not self.symbols_dict:
            self.write_terminal("[!] Error: No tuned hyperparameters found.")
            return
            
        self.btn_start.configure(state="disabled", text="TRAINING...", fg_color="#333333")
        self.btn_stop.configure(state="normal")
        self.symbol_results.clear()
        
        for sym in self.symbol_status_vars:
            self.symbol_status_vars[sym].set("Pending in Queue...")
            self.symbol_progress_vars[sym].set(0.0)
            self.symbol_title_vars[sym].set(f"■  {sym}  [ETA: Waiting...]")

        self.process = None
        self.is_stopped = False
        thread = threading.Thread(target=self.run_subprocess)
        thread.start()

    def stop_optimization(self):
        if hasattr(self, 'process') and self.process is not None:
            self.is_stopped = True
            self.process.terminate()
            self.log_queue.put(("[!] GYM TRAINING INTERRUPTED BY USER.", "#ff4444"))
        self.btn_stop.configure(state="disabled")

    def run_subprocess(self):
        self.log_queue.put("-" * 50)
        self.log_queue.put(" AURA: INITIATING MULTI-CORE RL TRAINING")
        self.log_queue.put("-" * 50)
        
        try:
            self.process = subprocess.Popen(
                [sys.executable, "-u", TRAIN_SCRIPT],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                cwd=BASE_DIR
            )
            
            for line in self.process.stdout:
                if self.is_stopped:
                    break
                self.log_queue.put(line)
                
            self.process.wait()
            
            if not self.is_stopped:
                self.log_queue.put("SUMMARY")
                self.log_queue.put("-" * 50)
                self.log_queue.put(" AURA: ALL TRAINING COMPLETE. Weights saved in rl/models.")
                self.log_queue.put("-" * 50)
                
        except Exception as e:
            self.log_queue.put((f"[!] Subprocess crashed/terminated: {e}", "#ff4444"))
            
        self.btn_start.configure(state="normal", text="START GYM TRAINING", fg_color="#0d5c46")
        self.btn_stop.configure(state="disabled")

    def print_optimization_summary(self):
        self.log_queue.put(("-" * 48, "#ffffff"))
        self.log_queue.put((" FINAL TRAINING SUMMARY", "#00ffcc"))
        self.log_queue.put(("-" * 48, "#ffffff"))
        
        for sym in self.symbols_dict.keys():
            sym_color = self.symbol_colors.get(sym, "#00ffcc")
            res = self.symbol_results.get(sym, None)
            
            if not res:
                self.log_queue.put((f" {sym.ljust(10)} | DID NOT RUN", "#777777"))
            elif res == "SUCCESS":
                self.log_queue.put((f" {sym.ljust(10)} | TRAINED | weights secured", sym_color))
        self.log_queue.put(("-" * 50, "#ffffff"))

if __name__ == "__main__":
    app = AuraRLTrainerGUI()
    app.mainloop()