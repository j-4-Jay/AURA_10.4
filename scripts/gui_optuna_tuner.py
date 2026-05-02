import os
import glob
import sys
import threading
import json
import subprocess
import time
import datetime
import customtkinter as ctk
import tkinter as tk
import queue
import re

ctk.set_appearance_mode("Dark")

# Exact Hardcoded Master Path
BASE_DIR = r"C:\Users\JAY\Documents\AURA (MT5 Trading)\AURA_MT5 RL Trading"
PARQUET_DIR = os.path.join(BASE_DIR, "data", "parquet_capsules")
OPTUNA_SCRIPT = os.path.join(BASE_DIR, "rl", "optuna_tuner.py")

class AuraOptunaGUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("AURA Institutional Tuner - PHASE 4 (OPTUNA)")
        self.geometry("1650x900")
        self.resizable(True, True)
        self.configure(fg_color="#0a0a0a")
        
        self.log_queue = queue.Queue()
        
        self.symbols_dict = self.scan_available_symbols_and_tfs()
        
        self.symbol_status_vars = {} 
        self.symbol_progress_vars = {} 
        self.symbol_results = {}
        self.symbol_completed_trials = {}
        self.symbol_cards = {}
        self.symbol_start_times = {} 
        
        self.result_json_paths = {}
        self.total_trials = 500  

        self.color_palette = ["#00ffcc", "#ff00cc", "#ffcc00", "#00ccff", "#ccff00", "#ff6600", "#cc00ff", "#00ff66"]
        self.symbol_colors = {}
        
        c_index = 0
        for sym in self.symbols_dict.keys():
            self.symbol_colors[sym] = self.color_palette[c_index % len(self.color_palette)]
            self.result_json_paths[sym] = os.path.join(BASE_DIR, "ea", "Files", "AURA_Configs", f"{sym}_params.json")
            c_index += 1

        self.build_ui()
        self.check_queue()

    def scan_available_symbols_and_tfs(self):
        os.makedirs(PARQUET_DIR, exist_ok=True)
        symbols_map = {}
        for f in os.listdir(PARQUET_DIR):
            if f.endswith(".parquet"):
                parts = f.split("_")
                if len(parts) >= 2:
                    sym = parts[0]
                    tf = parts[1]
                    if sym not in symbols_map:
                        symbols_map[sym] = set()
                    symbols_map[sym].add(tf)
        
        for sym in symbols_map:
            symbols_map[sym] = sorted(list(symbols_map[sym]))
            
        return dict(sorted(symbols_map.items()))

    def grade_numeric(self, got_value, planned_value, minimum_value, higher_is_better=True):
        try:
            got = float(got_value)
            planned = float(planned_value)
            minimum = float(minimum_value)
        except Exception:
            return "Normal"
            
        if higher_is_better:
            if got >= planned: return "Premium"
            if got >= minimum: return "Nice"
            return "Normal"
        else:
            if got <= planned: return "Premium"
            if got <= minimum: return "Nice"
            return "Normal"

    def grade_text(self, got_value, planned_value):
        if str(got_value).strip() == str(planned_value).strip():
            return "Premium"
        if str(got_value).strip() != "":
            return "Nice"
        return "Normal"

    def clear_children(self, widget):
        for child in widget.winfo_children():
            child.destroy()

    def make_detail_row(self, parent, metric, got_value, planned_value, minimum_value, grade):
        row = ctk.CTkFrame(parent, fg_color="#1f1f1f", corner_radius=4)
        row.pack(fill="x", padx=2, pady=1)  # Ultra slim padding
        
        grade_color = {"Premium": "#35d07f", "Nice": "#ffb347", "Normal": "#b0b0b0"}.get(grade, "#b0b0b0")
        
        cells = [
            (metric, "#ffffff"),
            (str(got_value), "#00ffcc"),
            (str(planned_value), "#c8d1ff"),
            (str(minimum_value), "#aaaaaa"),
            (grade, grade_color),
        ]
        
        for col_index, (value, color) in enumerate(cells):
            dyn_anchor = "w" if col_index == 0 else ("e" if col_index == 4 else "center")
            dyn_justify = "left" if col_index == 0 else ("right" if col_index == 4 else "center")
            
            label = ctk.CTkLabel(
                row, 
                text=value, 
                text_color=color,
                font=ctk.CTkFont(size=11, weight="bold" if col_index in [0, 4] else "normal"),
                anchor=dyn_anchor,
                justify=dyn_justify,
                wraplength=180 if col_index == 0 else 140
            )
            label.grid(row=0, column=col_index, sticky="ew", padx=6, pady=4)
            
        for col_index, weight in enumerate([4, 3, 3, 3, 2]):
            row.grid_columnconfigure(col_index, weight=weight)

    def build_optuna_detail_rows(self, sym, payload):
        rows = []
        timeframe = payload.get("timeframe_optimized", "Unknown")
        profit_factor = payload.get("profit_factor_tested", 0.0)
        
        circuit_breaker = payload.get("circuit_breaker") or {}
        indicators = payload.get("indicators") or {}
        strategies = payload.get("strategies") or {}
        trailing = payload.get("trailing_management") or {}
        
        strat_names = {
            "strat_1": "Fashionably Late Scalp",
            "strat_2": "The Magnet VWAP",
            "strat_3": "Whale Footprint FVG",
            "strat_4": "The Coil Squeeze",
            "strat_5": "Rubber Band Snap",
            "strat_6": "Shadow Thief",
            "strat_7": "Spark Plug"
        }
        
        active_strats = []
        for key, enabled in strategies.items():
            if enabled:
                active_strats.append(strat_names.get(key, key))
                
        trailing_map = {1: "Breakeven Trigger", 2: "ATR Chandelier Drop", 3: "Market Structure Trail"}
        trailing_name = trailing_map.get(trailing.get("trailing_type", 1), "Unknown")
        
        rows.append(("Symbol", sym, sym, sym, "Premium"))
        rows.append(("Timeframe optimized", timeframe, "Best selected timeframe", "Valid market TF", self.grade_text(timeframe, timeframe)))
        rows.append(("Profit factor tested", f"{profit_factor:.2f}", "3.20", "0.80", self.grade_numeric(profit_factor, 3.2, 0.8, higher_is_better=True)))
        rows.append(("Max drawdown %", circuit_breaker.get("global_max_drawdown_pct", "N/A"), "5.00", "5.00", self.grade_numeric(circuit_breaker.get("global_max_drawdown_pct", 999), 5.0, 5.0, higher_is_better=False)))
        
        rows.append(("EMA period", indicators.get("Optuna_EMA_Period", "N/A"), "50", "1", self.grade_numeric(indicators.get("Optuna_EMA_Period", 0), 50, 1, higher_is_better=True)))
        rows.append(("SL multiplier", indicators.get("Optuna_SL_Multiplier", "N/A"), "0.33", "0.10", self.grade_numeric(indicators.get("Optuna_SL_Multiplier", 0.0), 0.33, 0.10, higher_is_better=False)))
        rows.append(("TP multiplier", indicators.get("Optuna_TP_Multiplier", "N/A"), "1.00", "1.00", self.grade_numeric(indicators.get("Optuna_TP_Multiplier", 0.0), 1.0, 1.0, higher_is_better=True)))
        
        rows.append(("Active strategies", ", ".join(active_strats) if active_strats else "None", "Strongest enabled subset", "At least 1 active", self.grade_numeric(len(active_strats), 3, 1, higher_is_better=True)))
        rows.append(("Trailing type", trailing_name, "Volatility", "Fixed", self.grade_text(trailing_name, "ATR Chandelier Drop")))
        
        return rows

    def render_details_table(self, sym):
        try:
            card_state = self.symbol_cards.get(sym)
            if not card_state: return
            
            body = card_state['details_body']
            self.clear_children(body)
            
            result_path = self.result_json_paths.get(sym)
            payload = None
            if result_path and os.path.exists(result_path):
                with open(result_path, 'r') as json_file:
                    payload = json.load(json_file)
                    
            if not payload:
                ctk.CTkLabel(body, text="No saved result yet for this symbol.", text_color="#ff8888", font=ctk.CTkFont(size=11)).pack(anchor="w", padx=8, pady=6)
                return

            ctk.CTkLabel(body, text="Current Optimization Result", text_color="#ffffff", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=6, pady=(0, 6))

            table = ctk.CTkFrame(body, fg_color="#171717", corner_radius=6)
            table.pack(fill="x", padx=2, pady=(0, 8))
            
            header = ctk.CTkFrame(table, fg_color="#2a2a2a", corner_radius=4)
            header.pack(fill="x", padx=2, pady=(2, 4))
            
            columns = ["METRIC", "WHAT WE GOT", "WHAT WE PLANNED", "MINIMUM", "GRADE"]
            
            for col_index, text in enumerate(columns):
                dyn_anchor = "w" if col_index == 0 else ("e" if col_index == 4 else "center")
                dyn_justify = "left" if col_index == 0 else ("right" if col_index == 4 else "center")
                lbl = ctk.CTkLabel(header, text=text, text_color="#ffffff", font=ctk.CTkFont(size=9, weight="bold"), anchor=dyn_anchor, justify=dyn_justify)
                lbl.grid(row=0, column=col_index, sticky="ew", padx=6, pady=4)
                
            for col_index, weight in enumerate([4, 3, 3, 3, 2]):
                header.grid_columnconfigure(col_index, weight=weight)
                
            for metric, got, planned, minimum, grade in self.build_optuna_detail_rows(sym, payload):
                self.make_detail_row(table, metric, got, planned, minimum, grade)
                
        except Exception as e:
            self.write_terminal(f"[!] Error rendering table for {sym}: {e}", "#ff4444")

    def toggle_symbol_card(self, sym):
        try:
            card_state = self.symbol_cards.get(sym)
            if not card_state: return
            
            if card_state['expanded']:
                card_state['details_frame'].pack_forget()
                card_state['toggle_button'].configure(text=f"▶  {sym}")
                card_state['expanded'] = False
                return
            
            self.render_details_table(sym)
            card_state['details_frame'].pack(side="top", fill="x", padx=8, pady=(4, 8))
            card_state['toggle_button'].configure(text=f"▼  {sym}")
            card_state['expanded'] = True
        except Exception as e:
            self.write_terminal(f"[!] Error expanding card for {sym}: {e}", "#ff4444")

    def build_ui(self):
        self.left_frame = ctk.CTkFrame(self, width=280, corner_radius=0, fg_color="#121212")
        self.left_frame.pack(side="left", fill="y", padx=(10, 5), pady=10)
        self.left_frame.pack_propagate(False)
        
        ctk.CTkLabel(self.left_frame, text="1. Available Assets & TFs", font=ctk.CTkFont(size=16, weight="bold"), text_color="#ffffff").pack(pady=(15, 5))
        
        self.scroll_symbols = ctk.CTkScrollableFrame(self.left_frame, width=240, fg_color="#1a1a1a")
        self.scroll_symbols.pack(pady=5, fill="both", expand=True, padx=10)
        
        if not self.symbols_dict:
            ctk.CTkLabel(self.scroll_symbols, text="No Parquet files found. Data Prep (Phase 4).", text_color="#ff4444").pack(pady=20)
            
        for sym, tfs in self.symbols_dict.items():
            sym_frame = ctk.CTkFrame(self.scroll_symbols, fg_color="#222222", corner_radius=6)
            sym_frame.pack(fill="x", pady=5, padx=5)
            ctk.CTkLabel(sym_frame, text=f" {sym}", font=ctk.CTkFont(weight="bold"), text_color="#00ffcc").pack(anchor="w", padx=10, pady=(5,0))
            tf_str = ", ".join(tfs)
            ctk.CTkLabel(sym_frame, text=f"Charts: {tf_str}", font=ctk.CTkFont(size=11), text_color="#aaaaaa").pack(anchor="w", padx=10, pady=(0,5))
            
        self.btn_start = ctk.CTkButton(
            self.left_frame, text="START OPTUNA BATCH", font=ctk.CTkFont(size=14, weight="bold"),
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

        self.mid_frame = ctk.CTkFrame(self, width=950, corner_radius=0, fg_color="#121212")
        self.mid_frame.pack(side="left", fill="both", expand=True, padx=0, pady=10)
        self.mid_frame.pack_propagate(False)
        
        ctk.CTkLabel(self.mid_frame, text="2. Live Optimization Status", font=ctk.CTkFont(size=16, weight="bold"), text_color="#ffffff").pack(pady=(15, 0))
        ctk.CTkLabel(self.mid_frame, text="Click a symbol to expand the result table", font=ctk.CTkFont(size=11), text_color="#666666").pack(pady=(0, 10))
        
        self.scroll_status = ctk.CTkScrollableFrame(self.mid_frame, width=900, fg_color="#1a1a1a")
        self.scroll_status.pack(pady=10, fill="both", expand=True, padx=10)
        
        for sym in self.symbols_dict.keys():
            last_opt = "Waiting..."
            json_path = self.result_json_paths.get(sym)
            if json_path and os.path.exists(json_path):
                mtime = os.path.getmtime(json_path)
                dt_str = datetime.datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
                last_opt = f"Last Optimized: {dt_str}"

            card = ctk.CTkFrame(self.scroll_status, fg_color="#222222", corner_radius=6)
            card.pack(fill="x", pady=5, padx=5)
            
            header_frame = ctk.CTkFrame(card, fg_color="transparent")
            header_frame.pack(fill="x", padx=10, pady=(5, 0))
            
            toggle_button = ctk.CTkButton(
                header_frame, text=f"▶  {sym}", fg_color="transparent", hover_color="#2c2c2c", 
                text_color="#ffffff", anchor="w", height=28,
                command=lambda s=sym: self.toggle_symbol_card(s)
            )
            toggle_button.pack(side="left", fill="x", expand=True)
            
            status_var = ctk.StringVar(value=last_opt)
            self.symbol_status_vars[sym] = status_var
            ctk.CTkLabel(header_frame, textvariable=status_var, font=ctk.CTkFont(size=11), text_color="#888888").pack(side="right")
            
            prog_var = ctk.DoubleVar(value=0.0)
            self.symbol_progress_vars[sym] = prog_var
            sym_color = self.symbol_colors.get(sym, "#00ffcc")
            
            pb = ctk.CTkProgressBar(card, variable=prog_var, progress_color=sym_color, fg_color="#444444", height=8)
            pb.pack(fill="x", padx=10, pady=(5, 10))
            
            details_frame = ctk.CTkFrame(card, fg_color="#181818", corner_radius=4)
            details_body = ctk.CTkFrame(details_frame, fg_color="transparent")
            details_body.pack(fill="x", padx=6, pady=6)
            
            self.symbol_cards[sym] = {
                'toggle_button': toggle_button,
                'details_frame': details_frame,
                'details_body': details_body,
                'expanded': False,
                'card': card
            }

        self.right_frame = ctk.CTkFrame(self, width=380, corner_radius=0, fg_color="#121212")
        self.right_frame.pack(side="right", fill="y", expand=False, padx=(0, 10), pady=10)
        self.right_frame.pack_propagate(False)
        
        ctk.CTkLabel(self.right_frame, text="3. Optuna Terminal", font=ctk.CTkFont(size=16, weight="bold"), text_color="#ffffff").pack(pady=(15, 5))
        
        self.terminal = ctk.CTkTextbox(self.right_frame, bg_color="#0a0a0a", fg_color="#0a0a0a", text_color="#00ffcc", font=("Consolas", 12))
        self.terminal.pack(fill="both", expand=True, padx=10, pady=10)
        self.terminal.insert("0.0", "AURA System Ready. Start to begin sweeping all assets.\n")

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
        if "COMMENCING PHASE 4 STUDY FOR" in line:
            parts = line.split("FOR")
            if len(parts) > 1:
                sym = parts[1].strip().replace("...", "").strip()
                self.current_optimizing_symbol = sym
                self.symbol_start_times[sym] = time.time()
                if sym in self.symbol_status_vars:
                    self.symbol_status_vars[sym].set("Optimizing...")
                    self.symbol_progress_vars[sym].set(0.0)
                    
        elif "Vectorizing Indicators for" in line:
            match = re.search(r"for ([A-Za-z0-9]+)_", line)
            if match:
                sym = match.group(1)
                self.current_optimizing_symbol = sym
                if sym not in self.symbol_start_times:
                    self.symbol_start_times[sym] = time.time()
                if sym in self.symbol_status_vars and ("Waiting" in self.symbol_status_vars[sym].get() or "Last Optimized" in self.symbol_status_vars[sym].get()):
                    self.symbol_status_vars[sym].set("Optimizing...")
                    self.symbol_progress_vars[sym].set(0.0)

        if "Trial" in line and "finished" in line:
            sym = getattr(self, 'current_optimizing_symbol', None)
            if sym and sym in self.symbol_progress_vars:
                self.symbol_completed_trials[sym] = self.symbol_completed_trials.get(sym, 0) + 1
                trial_count = self.symbol_completed_trials[sym]
                prog_val = min(1.0, trial_count / self.total_trials)
                self.symbol_progress_vars[sym].set(prog_val)
                self.symbol_status_vars[sym].set(f"Optimizing ({trial_count}/{self.total_trials})...")

        if "BEST COMBINATION" in line and "PF:" in line:
            sym = getattr(self, 'current_optimizing_symbol', None)
            if not sym: return
            
            pf_value = line.split("PF:")[1].strip().split()[0] if "PF:" in line else "1.0"
            
            calc_time = "00:00:00"
            if "Calc Time:" in line:
                calc_time = line.split("Calc Time:")[1].strip().split()[0]
            else:
                elapsed = time.time() - self.symbol_start_times.get(sym, time.time())
                h, rem = divmod(elapsed, 3600)
                m, s = divmod(rem, 60)
                calc_time = f"{int(h):02d}:{int(m):02d}:{int(s):02d}"

            self.symbol_results[sym] = {"status": "SUCCESS", "pf": pf_value, "calc_time": calc_time}
            if sym in self.symbol_status_vars:
                self.symbol_status_vars[sym].set(f"[*] OK | PF: {pf_value} | Calc Time: {calc_time}")
                self.symbol_progress_vars[sym].set(1.0)
                if self.symbol_cards.get(sym, {}).get('expanded'):
                    self.render_details_table(sym)

        if "RECIPE GENERATED:" in line:
            match = re.search(r"([A-Za-z0-9]+)_params\.json", line)
            if match:
                sym = match.group(1)
                if sym in self.symbol_status_vars and self.symbol_progress_vars[sym].get() < 1.0:
                    self.symbol_progress_vars[sym].set(1.0)
                    if "Waiting" in self.symbol_status_vars[sym].get() or "Optimizing" in self.symbol_status_vars[sym].get():
                        self.symbol_status_vars[sym].set("[*] OK | JSON Generated")
                    if self.symbol_cards.get(sym, {}).get('expanded'):
                        self.render_details_table(sym)

        if "No profitable combinations found" in line:
            sym = getattr(self, 'current_optimizing_symbol', None)
            if sym:
                self.symbol_results[sym] = {"status": "FAILED", "pf": "0.0"}
                if sym in self.symbol_status_vars:
                    self.symbol_status_vars[sym].set("[!] Failed (Strict PF criteria)")
                    self.symbol_progress_vars[sym].set(1.0)

    def start_optimization(self):
        if not self.symbols_dict:
            self.write_terminal("[!] Error: No data found to optimize.")
            return
            
        self.btn_start.configure(state="disabled", text="OPTIMIZING...", fg_color="#333333")
        self.btn_stop.configure(state="normal")
        self.symbol_results.clear()
        
        for sym in self.symbol_status_vars:
            self.symbol_status_vars[sym].set("Pending...")
            self.symbol_progress_vars[sym].set(0.0)
            
            card_state = self.symbol_cards.get(sym)
            if card_state:
                self.clear_children(card_state['details_body'])
                if card_state['expanded']:
                    card_state['details_frame'].pack_forget()
                    card_state['toggle_button'].configure(text=f"▶  {sym}")
                    card_state['expanded'] = False

        self.process = None
        self.is_stopped = False
        thread = threading.Thread(target=self.run_subprocess)
        thread.start()

    def stop_optimization(self):
        if hasattr(self, 'process') and self.process is not None:
            self.is_stopped = True
            self.process.terminate()
            self.log_queue.put(("[!] PROCESS INTERRUPTED BY USER.", "#ff4444"))
        self.btn_stop.configure(state="disabled")

    def run_subprocess(self):
        self.log_queue.put("-" * 50)
        self.log_queue.put(" AURA: INITIATING COMPLETE BATCH OPTIMIZATION")
        self.log_queue.put("-" * 50)
        
        try:
            self.process = subprocess.Popen(
                [sys.executable, "-u", OPTUNA_SCRIPT],
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
                self.log_queue.put(" AURA: ALL BATCHES COMPLETE. JSON files generated in ea/Files/AURA_Configs.")
                self.log_queue.put("-" * 50)
                
        except Exception as e:
            self.log_queue.put((f"[!] Subprocess crashed/terminated: {e}", "#ff4444"))
            
        self.btn_start.configure(state="normal", text="START OPTUNA BATCH", fg_color="#0d5c46")
        self.btn_stop.configure(state="disabled")

    def print_optimization_summary(self):
        self.log_queue.put(("-" * 48, "#ffffff"))
        self.log_queue.put((" FINAL OPTIMIZATION SUMMARY", "#00ffcc"))
        self.log_queue.put(("-" * 48, "#ffffff"))
        
        for sym, tfs_available in self.symbols_dict.items():
            sym_color = self.symbol_colors.get(sym, "#00ffcc")
            res = self.symbol_results.get(sym, None)
            
            if not res:
                self.log_queue.put((f" {sym.ljust(10)} | DID NOT RUN / SKIPPED", "#777777"))
            elif res["status"] == "SUCCESS":
                self.log_queue.put((f" {sym.ljust(10)} | SECURED | Profit Factor: {res['pf']}", sym_color))
            else:
                self.log_queue.put((f" {sym.ljust(10)} | FAILED | No setup met criteria", "#ff4444"))
        self.log_queue.put(("-" * 50, "#ffffff"))

if __name__ == "__main__":
    app = AuraOptunaGUI()
    app.mainloop()