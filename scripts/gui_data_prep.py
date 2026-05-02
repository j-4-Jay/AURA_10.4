import os
import glob
import json
import time
import sys
import threading
import queue
import shutil
from datetime import datetime
import customtkinter as ctk
import tkinter as tk
import polars as pl

# [AURA-STRICT-PROTOCOL] Visual Data Preparation Engine V4.4 (Dynamic Info Board + EA Constructor)

ctk.set_appearance_mode("Dark")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_DIR = os.path.join(BASE_DIR, "data", "csv_landing")
PARQUET_DIR = os.path.join(BASE_DIR, "data", "parquet_capsules")
META_FILE = os.path.join(BASE_DIR, "data", "metadata.json")

# Strict EA Paths
EA_DIR = os.path.join(BASE_DIR, "ea", "Experts")
VERSIONS_DIR = os.path.join(EA_DIR, "Versions")

os.makedirs(CSV_DIR, exist_ok=True)
os.makedirs(PARQUET_DIR, exist_ok=True)
os.makedirs(EA_DIR, exist_ok=True)
os.makedirs(VERSIONS_DIR, exist_ok=True)

# ==============================================================================
# EA CONSTRUCTOR & VERSION CONTROL AGENT HELPERS
# ==============================================================================

def generate_mql5_skeleton(symbol, version):
    """ Generates strict AURA-compliant MQL5 boilerplate. """
    return f"""//+------------------------------------------------------------------+
//|                                              {symbol}_MasterEA.mq5 |
//|                                  AURA Institutional Trading System |
//|                                              [AURA-STRICT-PROTOCOL]|
//+------------------------------------------------------------------+
#property copyright "AURA Architecture"
#property link      "Strict Lock & Move Progression"
#property version   "{version}"

// ===================================================================
// 1. GLOBAL BASELINE RISK MANAGEMENT
// ===================================================================
input double GlobalMaxDrawdown = 5.0; // Max allowed DD %

// ===================================================================
// 2. HELPER CALCULATIONS & SHARED INDICATORS
// ===================================================================

// ===================================================================
// 3. ISOLATED STRATEGY LOGIC MODULES
// ===================================================================

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
  {{
   Print("[AURA] {symbol} Master EA v{version} Initialized.");
   return(INIT_SUCCEEDED);
  }}

void OnDeinit(const int reason)
  {{
   Print("[AURA] {symbol} Master EA shutting down.");
  }}

void OnTick()
  {{
   // Execution routing to specific Strategy Logic modules via ZMQ
  }}
//+------------------------------------------------------------------+
"""

def generate_parameter_skeleton(symbol):
    """ Generates the Institutional Parameter Skeleton matching the EA """
    return {
        "symbol": symbol,
        "global_risk": {
            "max_drawdown_pct": 5.0,
            "daily_loss_limit_usd": 1000
        },
        "strategies": {
            "mtf_fvg_sweep": {"enabled": True, "magic_number": 1001, "risk_pct": 1.0},
            "htf_trend_alignment": {"enabled": True, "magic_number": 1002, "risk_pct": 1.5},
            "ltf_order_block": {"enabled": False, "magic_number": 1003, "risk_pct": 0.5}
        }
    }

def get_latest_version(symbol_version_dir):
    """ Scans the symbol's version folder to find the latest version number """
    files = glob.glob(os.path.join(symbol_version_dir, "*.mq5"))
    if not files:
        return "1.00"
    
    versions = []
    for f in files:
        try:
            v_str = f.split("_v")[-1].replace(".mq5", "")
            versions.append(float(v_str))
        except ValueError:
            continue
            
    if not versions:
        return "1.00"
        
    latest = max(versions)
    return f"{(latest + 0.01):.2f}"

def trigger_ea_constructor_watcher():
    """ Auto-detects symbols from Parquets, manages Versioning, and updates the Experts path. """
    print("\n" + "="*60)
    print(" [AURA] VERSION CONTROL & EA CONSTRUCTOR AGENT WAKING UP")
    print("="*60)

    unique_symbols = set()
    for filename in os.listdir(PARQUET_DIR):
        if filename.endswith(".parquet"):
            sym = filename.split("_")[0]
            unique_symbols.add(sym)

    if not unique_symbols:
        print(" [!] No data capsules found. Watcher returning to sleep.")
        return

    for sym in sorted(unique_symbols):
        sym_version_dir = os.path.join(VERSIONS_DIR, sym)
        os.makedirs(sym_version_dir, exist_ok=True)

        active_ea_path = os.path.join(EA_DIR, f"{sym}_MasterEA.mq5")
        active_param_path = os.path.join(EA_DIR, f"{sym}_MasterEA_params.json")
        
        if not os.path.exists(active_ea_path):
            next_version = get_latest_version(sym_version_dir)
            
            versioned_ea_name = f"{sym}_MasterEA_v{next_version}.mq5"
            versioned_ea_path = os.path.join(sym_version_dir, versioned_ea_name)
            
            versioned_param_name = f"{sym}_MasterEA_params_v{next_version}.json"
            versioned_param_path = os.path.join(sym_version_dir, versioned_param_name)

            print(f"    [+] Constructing Missing Asset Architecture: {sym} (v{next_version})")
            
            mql5_code = generate_mql5_skeleton(sym, next_version)
            params_data = generate_parameter_skeleton(sym)
            
            with open(versioned_ea_path, "w", encoding="utf-8") as f:
                f.write(mql5_code)
            with open(versioned_param_path, "w", encoding="utf-8") as f:
                json.dump(params_data, f, indent=4)
                
            shutil.copy2(versioned_ea_path, active_ea_path)
            shutil.copy2(versioned_param_path, active_param_path)
            
            print(f"        -> Deployed to: Experts/{sym}_MasterEA.mq5")
        else:
            print(f"    [v] Validated active Master EA & Params for: {sym}")

    print("="*60)
    print(" [✅] Watcher execution complete. MT5 architecture synced.")
    print("="*60 + "\n")

# ==============================================================================
# VISUAL UI & ENGINE
# ==============================================================================

class RedirectStdout:
    """ Redirects terminal print() statements into the GUI textbox """
    def __init__(self, queue_obj):
        self.queue = queue_obj
    def write(self, string):
        self.queue.put(string)
    def flush(self):
        pass

class AuraDataPrepBatchUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("AURA Institutional Data Prep [BATCH COMPRESS]")
        self.geometry("900x550")
        self.resizable(False, False)
        self.configure(fg_color="#0a0a0a")
        
        self.metadata = self.load_metadata()
        self.csv_files = []
        self.checkbox_vars = {}
        self.display_map = {}
        self.checkbox_widgets = [] 
        self.log_queue = queue.Queue()
        self.is_processing = False

        self.build_ui()
        self.refresh_file_list()
        self.check_queue()

    def load_metadata(self):
        if os.path.exists(META_FILE):
            try:
                with open(META_FILE, "r") as f: return json.load(f)
            except: return {}
        return {}

    def save_metadata(self):
        with open(META_FILE, "w") as f:
            json.dump(self.metadata, f, indent=4)

    def build_ui(self):
        self.left_frame = ctk.CTkFrame(self, width=300, corner_radius=0, fg_color="#121212")
        self.left_frame.pack(side="left", fill="y", padx=(10, 5), pady=10)
        self.left_frame.pack_propagate(False)
        
        ctk.CTkLabel(self.left_frame, text="1. Select Raw CSV Data", font=ctk.CTkFont(size=16, weight="bold"), text_color="#ffffff").pack(pady=(15, 5))
        
        self.scroll_symbols = ctk.CTkScrollableFrame(self.left_frame, width=260, fg_color="#1a1a1a")
        self.scroll_symbols.pack(pady=5, fill="both", expand=True, padx=10)
        
        self.param_frame = ctk.CTkFrame(self.left_frame, fg_color="transparent")
        self.param_frame.pack(side="bottom", fill="x", padx=10, pady=(10, 15))

        self.btn_process = ctk.CTkButton(
            self.param_frame, 
            text="Clean Data", 
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#0d5c46", 
            hover_color="#128263", 
            text_color="#ffffff",
            corner_radius=100, 
            height=45,
            command=self.start_batch_process
        )
        self.btn_process.pack(pady=(0, 10), fill="x", padx=10)

        self.right_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="#121212")
        self.right_frame.pack(side="right", fill="both", expand=True, padx=(5, 10), pady=10)
        
        ctk.CTkLabel(self.right_frame, text="Information Terminal", font=ctk.CTkFont(size=16, weight="bold"), text_color="#ffffff").pack(pady=(15, 5))
        
        self.terminal = ctk.CTkTextbox(self.right_frame, bg_color="#0a0a0a", fg_color="#0a0a0a", text_color="#00ffcc", font=("Consolas", 12))
        self.terminal.pack(fill="both", expand=True, padx=10, pady=10)
        self.terminal.insert("0.0", "AURA Data Engine Ready.\nAwaiting batch selection...\n")

    def write_terminal(self, text):
        self.terminal.insert("end", text)
        self.terminal.see("end")

    def check_queue(self):
        while not self.log_queue.empty():
            msg = self.log_queue.get()
            self.write_terminal(msg)
        self.after(100, self.check_queue) 

    def update_info_display(self):
        if self.is_processing:
            return

        self.terminal.delete("1.0", "end")
        selected_names = [name for name, var in self.checkbox_vars.items() if var.get()]

        if not selected_names:
            self.terminal.insert("end", "AURA Data Engine Ready.\nAwaiting batch selection...\n")
            return

        for display_name in selected_names:
            filepath = self.display_map[display_name]
            filename = os.path.basename(filepath)
            
            self.terminal.insert("end", f"[{filename}]\n")
            
            try:
                size_mb = os.path.getsize(filepath) / (1024 * 1024)
                
                if filename in self.metadata:
                    meta = self.metadata[filename]
                    status_str = "Cleaned & Locked ✅" if meta.get("status") == "success" else "Error ⚠️"
                    last_run_raw = meta.get('last_run', 'Unknown')
                    rows_val = meta.get('rows', 0)
                    start_date = meta.get('start_date', 'Unknown')
                    end_date = meta.get('end_date', 'Unknown')
                    proc_time = meta.get('time_taken_sec', 0)
                    
                    self.terminal.insert("end", f"STATUS       : {status_str}\n")
                    self.terminal.insert("end", f"LAST RUN     : {last_run_raw}\n")
                    self.terminal.insert("end", f"ROWS         : {rows_val:,}\n")
                    self.terminal.insert("end", f"DURATION     : {start_date} to {end_date}\n")
                    self.terminal.insert("end", f"PROCESS TIME : {proc_time} seconds\n")
                else:
                    self.terminal.insert("end", f"STATUS       : UNPROCESSED ❌\n")
                    self.terminal.insert("end", f"LAST RUN     : N/A\n")
                    self.terminal.insert("end", f"ROWS         : Unknown\n")
                    self.terminal.insert("end", f"DURATION     : Unknown\n")
                    self.terminal.insert("end", f"PROCESS TIME : N/A\n")
                    
                self.terminal.insert("end", f"RAW SIZE     : {size_mb:.2f} MB\n")
                self.terminal.insert("end", "-" * 50 + "\n\n")
                
            except Exception as e:
                self.terminal.insert("end", f"    [!] Error reading info for {filename}: {str(e)}\n\n")

    def refresh_file_list(self):
        for widget in self.scroll_symbols.winfo_children():
            widget.destroy()
            
        self.csv_files = glob.glob(os.path.join(CSV_DIR, "*.csv"))
        self.display_map.clear()
        self.checkbox_vars.clear()
        self.checkbox_widgets.clear()

        if not self.csv_files:
            ctk.CTkLabel(self.scroll_symbols, text="No CSV files found in landing folder.", text_color="#ff4444").pack(pady=20)
            self.btn_process.configure(state="disabled", fg_color="#333333")
            return

        for filepath in self.csv_files:
            filename = os.path.basename(filepath)
            
            if filename in self.metadata:
                status = self.metadata[filename].get("status", "error")
                display_name = f"✅ {filename}" if status == "success" else f"⚠️ {filename}"
            else:
                display_name = f"❌ {filename}"

            self.display_map[display_name] = filepath
            var = tk.BooleanVar(value=False)
            self.checkbox_vars[display_name] = var
            
            cb = ctk.CTkCheckBox(
                self.scroll_symbols, 
                text=display_name, 
                variable=var,
                fg_color="#00ffcc", 
                hover_color="#00ccaa", 
                text_color="#cccccc",
                command=self.update_info_display
            )
            cb.pack(anchor="w", pady=8, padx=10)
            self.checkbox_widgets.append(cb)
            
        self.btn_process.configure(state="normal", fg_color="#0d5c46")

    def parse_and_clean_datetime(self, d_val, t_val):
        d_str = str(d_val).strip()
        t_str = str(t_val).strip() if t_val is not None else ""
        
        if " " in d_str:
            parts = d_str.split(" ")
            d_str = parts[0]
            if len(parts) > 1 and ":" in parts[1]:
                t_str = parts[1]

        d_str = d_str.replace(".", "-")
        d_parts = d_str.split("-")
        
        if len(d_parts) > 3:
            d_parts = d_parts[:3] 
            
        if len(d_parts) == 3:
            if len(d_parts[0]) == 4:
                final_date = f"{d_parts[2]}:{d_parts[1]}:{d_parts[0]}"
            else:
                final_date = f"{d_parts[0]}:{d_parts[1]}:{d_parts[2]}"
        else:
            final_date = d_str

        if t_str and "00:00:00" not in t_str and t_str.lower() != "none" and t_str.lower() != "null":
            t_clean = t_str.split(" ")[0]
            return f"{final_date} {t_clean}"
            
        return final_date

    def start_batch_process(self):
        selected = [name for name, var in self.checkbox_vars.items() if var.get()]
        if not selected:
            self.terminal.delete("1.0", "end")
            self.write_terminal("[!] Error: No datasets selected for cleaning.\n")
            return
            
        self.is_processing = True
        self.btn_process.configure(state="disabled", text="CLEANING...", fg_color="#333333")
        
        for cb in self.checkbox_widgets:
            cb.configure(state="disabled")

        self.terminal.delete("1.0", "end") 
        sys.stdout = RedirectStdout(self.log_queue)
        
        thread = threading.Thread(target=self.run_batch_polars, args=(selected,))
        thread.start()

    def run_batch_polars(self, selected_names):
        print("="*50)
        print(" [AURA] INITIATING BATCH DATA CLEANING")
        print("="*50)
        
        total_time = 0
        total_rows_processed = 0

        for display_name in selected_names:
            filepath = self.display_map[display_name]
            filename = os.path.basename(filepath)
            name_only = os.path.splitext(filename)[0]
            target_parquet = os.path.join(PARQUET_DIR, f"{name_only}.parquet")
            
            print(f"\n[*] Target Acquired: {filename}")
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

        self.save_metadata()
        
        # --- PHASE 3 PIPELINE BRIDGE: TRIGGER EA CONSTRUCTOR ---
        trigger_ea_constructor_watcher()

        print("\n" + "="*50)
        print(f" [AURA] BATCH PROCESS COMPLETE.")
        print(f" -> Total Data Processed: {total_rows_processed:,} bars.")
        print(f" -> Total Processing Time: {total_time:.2f} seconds.")
        print("="*50)
        
        sys.stdout = sys.__stdout__
        self.is_processing = False
        
        self.after(0, self.refresh_file_list)
        self.after(0, lambda: self.btn_process.configure(state="normal", text="Clean Data", fg_color="#0d5c46"))

if __name__ == "__main__":
    app = AuraDataPrepBatchUI()
    app.mainloop()