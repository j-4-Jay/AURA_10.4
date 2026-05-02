import os
import shutil
import time
import ctypes
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# [AURA-STRICT-PROTOCOL] Phase 3 - Seamless Versioning & Automated MT5 Sync Corrected

# =====================================================================
# WARNING: PASTE YOUR EXACT MT5 "MQL5" FOLDER PATH HERE
# =====================================================================
MT5_MQL5_DIR = r"C:\\Users\\JAY\\AppData\\Roaming\\MetaQuotes\\Terminal\\53785E099C927DB68A545C249CDBCE06\\MQL5"# =====================================================================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AURA_EA_DIR = os.path.join(BASE_DIR, "ea")

class AuraMT5SyncHandler(FileSystemEventHandler):
    def __init__(self):
        self.last_triggered = {}

    def on_modified(self, event):
        self.process_event(event)
        
    def on_created(self, event):
        self.process_event(event)

    def process_event(self, event):
        if event.is_directory:
            return
            
        filepath = event.src_path
        
        # [CRITICAL FIX] Prevent Infinite Loop: Completely ignore anything inside a 'Versions' folder
        if "\\Versions\\" in filepath or "/Versions/" in filepath:
            return
            
        ext = os.path.splitext(filepath)[1].lower()

        # Only trigger on MQL5 source and compiled files
        if ext not in ['.mq5', '.mqh', '.ex5']:
            return

        # Debounce: Prevent double-firing when code editors truncate/write/compile
        current_time = time.time()
        if filepath in self.last_triggered and (current_time - self.last_triggered[filepath]) < 2:
            return
        self.last_triggered[filepath] = current_time

        filename = os.path.basename(filepath)
        
        # Trigger Native Windows Dialog Box (Forced on top of all windows)
        msg = f"[AURA SYSTEM]\n\nFile detected: {filename}\n\nSync to MT5 terminal and lock a local version?"
        response = ctypes.windll.user32.MessageBoxW(0, msg, "AURA-STRICT-PROTOCOL: Sync Required", 4 | 32 | 4096)

        if response == 6: # User clicked 'Yes'
            self.sync_and_version(filepath)
        else:
            print(f"[AURA] Sync aborted for {filename} by user.")

    def sync_and_version(self, filepath):
        filename = os.path.basename(filepath)
        file_dir = os.path.dirname(filepath)
        name, ext = os.path.splitext(filename)

        # -------------------------------------------------------------
        # 1. PUSH TO MT5 (Maintaining original un-versioned name)
        # -------------------------------------------------------------
        if ext.lower() in ['.mq5', '.ex5']:
            # All .mq5 and .ex5 files go to Experts\AURA
            dest_path = os.path.join(MT5_MQL5_DIR, "Experts", "AURA", filename)
        elif ext.lower() == '.mqh':
            # All .mqh files go to Include\AURA
            dest_path = os.path.join(MT5_MQL5_DIR, "Include", "AURA", filename)
        else:
            # Fallback for anything else
            rel_path = os.path.relpath(filepath, AURA_EA_DIR)
            dest_path = os.path.join(MT5_MQL5_DIR, rel_path)
            
        try:
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            shutil.copy2(filepath, dest_path)
            print(f"[\u2713] SYNCED TO MT5: {dest_path}")
        except Exception as e:
            print(f"[!] FAILED TO SYNC TO MT5: {e}")
            return

        # -------------------------------------------------------------
        # 2. LOCAL SEAMLESS VERSIONING (Lock & Move Protocol)
        # -------------------------------------------------------------
        
        # Determine the correct local version directory based on file type
        if "MasterEA" in name and ext in ['.mq5', '.ex5']:
            # Extract the symbol (e.g., "EURUSDm" from "EURUSDm_MasterEA")
            symbol = name.replace("_MasterEA", "")
            
            # Target path: ea\Experts\Versions\<Symbol>\
            version_dir = os.path.join(AURA_EA_DIR, "Experts", "Versions", symbol)
        else:
            # Non-EA files (like .mqh Includes) get a local Versions folder in their current directory
            version_dir = os.path.join(file_dir, "Versions")

        os.makedirs(version_dir, exist_ok=True)

        # Determine the next sequence number (v1, v2, v3...)
        v_num = 1
        while os.path.exists(os.path.join(version_dir, f"{name}_v{v_num}{ext}")):
            v_num += 1

        versioned_name = f"{name}_v{v_num}{ext}"
        version_path = os.path.join(version_dir, versioned_name)

        shutil.copy2(filepath, version_path)
        print(f"[\u2713] VERSION LOCKED : {version_path}")
        print("-" * 60)

if __name__ == "__main__":
    if "YOUR_HASH_HERE" in MT5_MQL5_DIR:
        print("[!] ERROR: You must edit the script and add your MT5 MQL5 directory path.")
        exit(1)
        
    print(f"[AURA] Booting Seamless MT5 Sync Daemon...")
    print(f"[*] Watching Directory: {AURA_EA_DIR}")
    print(f"[*] Target MT5 Directory: {MT5_MQL5_DIR}")
    
    event_handler = AuraMT5SyncHandler()
    observer = Observer()
    observer.schedule(event_handler, AURA_EA_DIR, recursive=True)
    observer.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        print("\n[AURA] Sync Daemon Terminated.")
        
    observer.join()