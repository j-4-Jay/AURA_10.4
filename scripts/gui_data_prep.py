import os
import glob
import json
import time
import sys
import threading
import queue
from datetime import datetime
import customtkinter as ctk
import tkinter as tk
import polars as pl

# [AURA-STRICT-PROTOCOL] Visual Data Preparation Engine V5.0 (Pure Data Engine)

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("green")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_DIR = os.path.join(BASE_DIR, "data", "csv_landing")
PARQUET_DIR = os.path.join(BASE_DIR, "data", "parquet_capsules")
META_FILE = os.path.join(BASE_DIR, "data", "metadata.json")

# Ensure critical data directories exist
os.makedirs(CSV_DIR, exist_ok=True)
os.makedirs(PARQUET_DIR, exist_ok=True)

# ==============================================================================
# VISUAL UI & ENGINE
# ==============================================================================

class RedirectStdout:
    def __init__(self, queue_obj): self.queue = queue_obj
    def write(self, string): self.queue.put(string)
    def flush(self): pass

class AuraDataPrepBatchUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("AURA Institutional Data Prep [PURE ENGINE]")
        self.geometry("1000x650")
        self.configure(fg_color="#0a0a0a")
        
        self.metadata = self.load_metadata()
        self.file_map = {}     # { "ETHUSDm": ["Daily", "M1", "H1"] }
        self.display_map = {}  # { ("ETHUSDm", "Daily"): "path/to/ETHUSDm_Daily_***.csv" }
        self.ui_vars = {}      
        self.ui_frames = {}    
        self.log_queue = queue.Queue()
        self.is_processing = False
        self.stop_event = threading.Event()

        self.scan_csv_files()
        self.build_ui()
        self.check_queue()

    def load_metadata(self):
        if os.path.exists(META_FILE):
            try:
                with open(META_FILE, "r") as f: return json.load(f)
            except: return {}
        return {}

    def save_metadata(self):
        with open(META_FILE, "w") as f: json.dump(self.metadata, f, indent=4)

    def scan_csv_files(self):
        """ Perfectly parses format: Symbol_Timeframe_Junk.csv """
        self.file_map.clear()
        self.display_map.clear()
        
        csv_files = glob.glob(os.path.join(CSV_DIR, "*.csv"))
        for filepath in csv_files:
            filename = os.path.basename(filepath)
            name_only = os.path.splitext(filename)[0]
            
            # Split by the FIRST underscore to isolate the exact Symbol
            parts = name_only.split("_")
            if len(parts) >= 2:
                sym = parts[0]       
                tf_raw = parts[1]    
            else:
                sym = name_only
                tf_raw = "Base"
                
            if sym not in self.file_map: self.file_map[sym] = []
            
            # Prevent duplicate Timeframes if there are multiple junk files
            if tf_raw not in self.file_map[sym]:
                self.file_map[sym].append(tf_raw)
                self.display_map[(sym, tf_raw)] = filepath
            
        # Custom sort logic
        sort_order = {"M1":1, "M2":2, "M3":3, "M5":4, "M10":5, "M15":6, "M30":7, 
                      "H1":8, "H2":9, "H4":10, "Daily":11, "D":11, "W":12, "Month":13}
        for sym in self.file_map:
            self.file_map[sym].sort(key=lambda x: sort_order.get(x, 99))

    def clean_tf_name(self, tf_str):
        """ Maps raw string like 'Daily' to purely 'D' """
        mapping = {
            "Daily": "D", "1440": "D", "10080": "W", "43200": "Month",
            "60": "H1", "120": "H2", "240": "H4",
            "1": "M1", "5": "M5", "15": "M15", "30": "M30"
        }
        return mapping.get(tf_str, tf_str)

    def build_ui(self):
        self.grid_columnconfigure(0, weight=3) # Left Panel
        self.grid_columnconfigure(1, weight=7) # Right Panel
        self.grid_rowconfigure(0, weight=1)
        
        # ==========================================
        # LEFT PANEL: THE HIERARCHICAL TREE
        # ==========================================
        self.left_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="#121212")
        self.left_frame.grid(row=0, column=0, sticky="nsew", padx=(10, 5), pady=10)
        self.left_frame.grid_rowconfigure(2, weight=1)
        
        ctk.CTkLabel(self.left_frame, text="DATA VAULT (CSV)", font=ctk.CTkFont(size=16, weight="bold"), text_color="#ffffff").grid(row=0, column=0, pady=(15, 5))
        
        self.select_all_var = ctk.BooleanVar(value=True) # Default ON
        self.chk_select_all = ctk.CTkCheckBox(
            self.left_frame, text="Select All Synced Symbols", variable=self.select_all_var, 
            command=self.on_select_all, font=ctk.CTkFont(size=14, weight="bold"), fg_color="#0d5c46", hover_color="#128263"
        )
        self.chk_select_all.grid(row=1, column=0, sticky="ew", padx=15, pady=5)
        
        self.tree_scroll = ctk.CTkScrollableFrame(self.left_frame, fg_color="#1a1a1a")
        self.tree_scroll.grid(row=2, column=0, sticky="nsew", padx=10, pady=(5, 10))
        
        if not self.file_map:
            ctk.CTkLabel(self.tree_scroll, text="No CSV files found in data/csv_landing/", text_color="#ff4444").pack(pady=20)
        
        for sym, tfs in self.file_map.items():
            sym_var = ctk.BooleanVar(value=True) # Default ON
            
            # --- PARENT SYMBOL ROW (Clickable & Stretched) ---
            row_frame = ctk.CTkFrame(self.tree_scroll, fg_color="#222222", corner_radius=5, cursor="hand2")
            row_frame.pack(fill="x", pady=(8, 0), padx=2)
            
            row_frame.bind("<Button-1>", lambda e, s=sym: self.toggle_tree(s))
            
            lbl_arrow = ctk.CTkLabel(row_frame, text="▶", font=ctk.CTkFont(size=12), text_color="#aaaaaa", width=25)
            lbl_arrow.pack(side="left", padx=(5,0), pady=8)
            lbl_arrow.bind("<Button-1>", lambda e, s=sym: self.toggle_tree(s))
            
            chk_sym = ctk.CTkCheckBox(row_frame, text=sym, variable=sym_var, font=ctk.CTkFont(size=15, weight="bold"),
                                      command=lambda s=sym: self.on_symbol_check(s))
            chk_sym.pack(side="left", padx=5, fill="x", expand=True)
            
            # --- CHILD FRAME (Collapsed by Default) ---
            child_frame = ctk.CTkFrame(self.tree_scroll, fg_color="transparent")
            
            self.ui_vars[sym] = {"var": sym_var, "tfs": {}}
            self.ui_frames[sym] = {"arrow": lbl_arrow, "child_frame": child_frame, "row_frame": row_frame}
            
            total_tfs = len(tfs)
            for i, tf in enumerate(tfs):
                tf_var = ctk.BooleanVar(value=True) # Default ON
                tf_clean_name = self.clean_tf_name(tf)
                
                # ASCII Branching Logic
                branch_char = "└──" if i == total_tfs - 1 else "├──"
                ascii_text = f"  {branch_char}  {tf_clean_name}"
                
                tf_row = ctk.CTkFrame(child_frame, fg_color="transparent")
                tf_row.pack(fill="x")
                
                chk_tf = ctk.CTkCheckBox(tf_row, text=ascii_text, variable=tf_var, font=ctk.CTkFont(family="Consolas", size=14, weight="bold"),
                                         text_color="#00ffcc", command=lambda s=sym: self.on_tf_check(s))
                chk_tf.pack(anchor="w", padx=25, pady=4, fill="x", expand=True)
                self.ui_vars[sym]["tfs"][tf] = tf_var

        # ==========================================
        # RIGHT PANEL: TERMINAL & ENGINE
        # ==========================================
        self.right_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="#121212")
        self.right_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 10), pady=10)
        
        ctk.CTkLabel(self.right_frame, text="Information Terminal", font=ctk.CTkFont(size=16, weight="bold"), text_color="#ffffff").pack(pady=(15, 5))
        
        self.terminal = ctk.CTkTextbox(self.right_frame, bg_color="#0a0a0a", fg_color="#0a0a0a", text_color="#00ffcc", font=("Consolas", 12))
        self.terminal.pack(fill="both", expand=True, padx=10, pady=(5, 10))
        self.terminal.insert("0.0", "AURA Data Engine Ready.\nAll Data selected by default.\n")
        
        self.control_frame = ctk.CTkFrame(self.right_frame, fg_color="#1a1a1a")
        self.control_frame.pack(fill="x", side="bottom", padx=10, pady=10)
        
        self.lbl_eta = ctk.CTkLabel(self.control_frame, text="ETA: --:-- | Progress: 0%", font=("Arial", 12, "bold"))
        self.lbl_eta.pack(pady=(10, 0))
        
        self.progress = ctk.CTkProgressBar(self.control_frame, progress_color="#0d5c46")
        self.progress.pack(fill="x", padx=20, pady=10)
        self.progress.set(0)
        
        self.btn_frame = ctk.CTkFrame(self.control_frame, fg_color="transparent")
        self.btn_frame.pack(fill="x", pady=10)
        
        self.btn_process = ctk.CTkButton(
            self.btn_frame, text="CLEAN DATA", font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#0d5c46", hover_color="#128263", height=40, command=self.start_batch_process
        )
        self.btn_process.pack(side="left", fill="x", expand=True, padx=(20, 5))
        
        self.btn_stop = ctk.CTkButton(
            self.btn_frame, text="EMERGENCY STOP", font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#E63946", hover_color="#C1121F", height=40, state="disabled", command=self.stop_process
        )
        self.btn_stop.pack(side="right", fill="x", expand=True, padx=(5, 20))

    # --- TREE CASCADE LOGIC ---
    def toggle_tree(self, sym):
        child_frame = self.ui_frames[sym]["child_frame"]
        arrow = self.ui_frames[sym]["arrow"]
        row_frame = self.ui_frames[sym]["row_frame"]
        
        if child_frame.winfo_ismapped():
            child_frame.pack_forget()
            arrow.configure(text="▶")
            row_frame.configure(fg_color="#222222") # Default dark
        else:
            child_frame.pack(fill="x", after=row_frame)
            arrow.configure(text="▼")
            row_frame.configure(fg_color="#1a3b2e") # Highlight when expanded

    def on_select_all(self):
        state = self.select_all_var.get()
        for sym, data in self.ui_vars.items():
            data["var"].set(state)
            for tf_var in data["tfs"].values():
                tf_var.set(state)

    def on_symbol_check(self, sym):
        state = self.ui_vars[sym]["var"].get()
        for tf_var in self.ui_vars[sym]["tfs"].values():
            tf_var.set(state)
        self.check_all_state()

    def on_tf_check(self, sym):
        all_checked = all(v.get() for v in self.ui_vars[sym]["tfs"].values())
        self.ui_vars[sym]["var"].set(all_checked)
        self.check_all_state()

    def check_all_state(self):
        all_sym_checked = all(data["var"].get() for data in self.ui_vars.values())
        if len(self.ui_vars) > 0:
            self.select_all_var.set(all_sym_checked)

    # --- ENGINE & LOGIC ---
    def write_terminal(self, text):
        self.terminal.insert("end", text)
        self.terminal.see("end")

    def check_queue(self):
        while not self.log_queue.empty():
            self.write_terminal(self.log_queue.get())
        self.after(100, self.check_queue) 

    def stop_process(self):
        self.stop_event.set()
        print("\n[!] EMERGENCY STOP INITIATED. Halting after current operation...")

    def parse_and_clean_datetime(self, d_val, t_val):
        d_str = str(d_val).strip()
        t_str = str(t_val).strip() if t_val is not None else ""
        if " " in d_str:
            parts = d_str.split(" ")
            d_str = parts[0]
            if len(parts) > 1 and ":" in parts[1]: t_str = parts[1]

        d_str = d_str.replace(".", "-")
        d_parts = d_str.split("-")
        if len(d_parts) > 3: d_parts = d_parts[:3] 
            
        if len(d_parts) == 3:
            if len(d_parts[0]) == 4: final_date = f"{d_parts[2]}:{d_parts[1]}:{d_parts[0]}"
            else: final_date = f"{d_parts[0]}:{d_parts[1]}:{d_parts[2]}"
        else: final_date = d_str

        if t_str and "00:00:00" not in t_str and t_str.lower() not in ["none", "null"]:
            t_clean = t_str.split(" ")[0]
            return f"{final_date} {t_clean}"
        return final_date

    def start_batch_process(self):
        selected_files = []
        for sym, data in self.ui_vars.items():
            for tf, tf_var in data["tfs"].items():
                if tf_var.get(): selected_files.append((sym, tf))

        if not selected_files:
            self.terminal.delete("1.0", "end")
            self.write_terminal("[!] Error: No datasets selected for cleaning.\n")
            return
            
        self.is_processing = True
        self.stop_event.clear()
        self.progress.set(0)
        self.lbl_eta.configure(text="ETA: Calculating... | Progress: 0%")
        self.btn_process.configure(state="disabled", text="CLEANING...", fg_color="#333333")
        self.btn_stop.configure(state="normal")

        self.terminal.delete("1.0", "end") 
        sys.stdout = RedirectStdout(self.log_queue)
        
        thread = threading.Thread(target=self.run_batch_polars, args=(selected_files,))
        thread.start()

    def run_batch_polars(self, selected_files):
        print("="*50)
        print(" [AURA] INITIATING BATCH DATA CLEANING")
        print("="*50)
        
        total_time = 0
        total_rows_processed = 0
        total_files = len(selected_files)
        start_time_global = time.time()

        for idx, (sym, tf) in enumerate(selected_files):
            if self.stop_event.is_set():
                print("\n[!] Process aborted by user.")
                break

            filepath = self.display_map[(sym, tf)]
            filename = os.path.basename(filepath)
            
            # Standardize parquet output name (e.g., ETHUSDm_D.parquet)
            tf_clean = self.clean_tf_name(tf)
            target_parquet = os.path.join(PARQUET_DIR, f"{sym}_{tf_clean}.parquet")
            
            print(f"\n[*] Target Acquired: {sym} ({tf_clean})")
            print(f"    -> Cleaning and structuring data...")

            try:
                start_time = time.time()
                
                with open(filepath, 'r') as f:
                    first_line = f.readline()
                    sep = '\t' if '\t' in first_line else ','
                
                df = pl.read_csv(filepath, separator=sep)
                rows = len(df)
                total_rows_processed += rows
                
                cols = df.columns
                date_col = next((c for c in cols if "date" in c.lower()), cols[0])
                time_col = next((c for c in cols if "time" in c.lower() and c != date_col), None)
                
                start_formatted = self.parse_and_clean_datetime(df[date_col][0], df[time_col][0] if time_col else None)
                end_formatted = self.parse_and_clean_datetime(df[date_col][-1], df[time_col][-1] if time_col else None)
                
                print(f"    -> Extracted {rows:,} bars. ({start_formatted} to {end_formatted})")
                print(f"    -> Packing into Parquet Engine...")
                
                df.write_parquet(target_parquet)
                
                time_taken = round(time.time() - start_time, 2)
                total_time += time_taken
                now_formatted = datetime.now().strftime("%d:%m:%Y %H:%M:%S")

                self.metadata[filename] = {
                    "status": "success",
                    "last_run": now_formatted,
                    "rows": rows,
                    "start_date": start_formatted,
                    "end_date": end_formatted,
                    "time_taken_sec": time_taken,
                    "parquet_path": target_parquet
                }
                print(f"    [✅] CLEANING SUCCESS | Processing Time: {time_taken}s")

            except Exception as e:
                self.metadata[filename] = {"status": "error", "error_msg": str(e)}
                print(f"    [❌] FATAL ERROR DURING CLEANING:\n{str(e)}")

            pct = (idx + 1) / total_files
            self.after(0, lambda p=pct: self.progress.set(p))
            
            elapsed = time.time() - start_time_global
            time_per_file = elapsed / (idx + 1)
            remaining_files = total_files - (idx + 1)
            eta_sec = int(remaining_files * time_per_file)
            
            m, s = divmod(eta_sec, 60)
            eta_str = f"ETA: {m}m {s}s" if eta_sec > 0 else "ETA: Almost done..."
            pct_str = f"Progress: {int(pct * 100)}%"
            self.after(0, lambda e=eta_str, p=pct_str: self.lbl_eta.configure(text=f"{e} | {p}"))

        self.save_metadata()

        print("\n" + "="*50)
        print(f" [AURA] BATCH PROCESS COMPLETE.")
        print(f" -> Total Data Processed: {total_rows_processed:,} bars.")
        print(f" -> Total Processing Time: {total_time:.2f} seconds.")
        print("="*50)
        
        sys.stdout = sys.__stdout__
        self.is_processing = False
        
        self.after(0, lambda: self.btn_process.configure(state="normal", text="CLEAN DATA", fg_color="#0d5c46"))
        self.after(0, lambda: self.btn_stop.configure(state="disabled"))

if __name__ == "__main__":
    app = AuraDataPrepBatchUI()
    app.mainloop()