import os
import sys
import subprocess
import threading
import time
import signal
import webbrowser
from pathlib import Path
from colorama import init, Fore, Style

# [AURA-STRICT-PROTOCOL] Single Boot Orchestrator (Single Browser Edition)
init(autoreset=True)

# THE FIX: Point BASE_DIR one level up to the root AURA_10.4 directory
BASE_DIR = str(Path(__file__).parent.parent.resolve())
VENV_PYTHON = sys.executable  # Automatically uses the active .venv python

# Define the subsystems
SYSTEMS = {
    "BACKEND": {
        # THE FIX: run_backend.py is now explicitly called from the scripts folder
        "command": [VENV_PYTHON, os.path.join(BASE_DIR, "scripts", "run_backend.py")],
        "color": Fore.GREEN,
        "port": 8000,
        "process": None
    },
    "FRONTEND": {
        "command": ["npm", "run", "dev"],
        "cwd": os.path.join(BASE_DIR, "frontend"),
        "color": Fore.CYAN,
        "port": 3000,
        "process": None
    }
}

def stream_logs(process, name, color):
    """ Reads the stdout/stderr of a subprocess and prints it with a colored prefix """
    for line in iter(process.stdout.readline, b''):
        decoded_line = line.decode('utf-8', errors='ignore').strip()
        if decoded_line:
            print(f"{color}[{name}]{Style.RESET_ALL} {decoded_line}")
            
    for line in iter(process.stderr.readline, b''):
        decoded_line = line.decode('utf-8', errors='ignore').strip()
        if decoded_line:
            print(f"{Fore.RED}[{name} ERROR]{Style.RESET_ALL} {decoded_line}")

def shutdown_handler(signum, frame):
    """ Gracefully terminates all child processes when Ctrl+C is pressed """
    print(f"\n{Fore.MAGENTA}[AURA CORE] Shutting down ecosystem...{Style.RESET_ALL}")
    for name, sys_data in SYSTEMS.items():
        proc = sys_data["process"]
        if proc and proc.poll() is None:
            print(f"[*] Terminating {name}...")
            proc.terminate()
            proc.wait(timeout=3)
    print(f"{Fore.MAGENTA}[AURA CORE] Ecosystem offline. Goodbye.{Style.RESET_ALL}")
    sys.exit(0)

def boot_aura():
    print(f"{Fore.MAGENTA}==================================================")
    print(f"      [AURA] INSTITUTIONAL BOOT COMMANDER")
    print(f"=================================================={Style.RESET_ALL}\n")
    
    signal.signal(signal.SIGINT, shutdown_handler)

    # Launch Subsystems
    for name, sys_data in SYSTEMS.items():
        print(f"[*] Igniting {name}...")
        work_dir = sys_data.get("cwd", BASE_DIR)
        # Use shell=True for Windows npm compatibility, avoid for Python scripts
        use_shell = (name == "FRONTEND")
        try:
            proc = subprocess.Popen(
                sys_data["command"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=work_dir,
                shell=use_shell
            )
            sys_data["process"] = proc
            thread = threading.Thread(target=stream_logs, args=(proc, name, sys_data["color"]), daemon=True)
            thread.start()
            time.sleep(2 if name == "FRONTEND" else 1)
        except FileNotFoundError as e:
            print(f"{Fore.RED}[ERROR] Failed to start {name}: {e}{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}[WARN] Ensure npm is installed and in PATH for FRONTEND{Style.RESET_ALL}")
            raise

    print(f"\n{Fore.MAGENTA}[AURA CORE] All systems nominal. Press Ctrl+C to terminate.{Style.RESET_ALL}\n")
    
    # Wait for Next.js to be ready, then open browser
    print(f"{Fore.CYAN}[FRONTEND] Launching UI Command Center...{Style.RESET_ALL}")
    time.sleep(3)
    webbrowser.open("http://localhost:3000")
    print(f"{Fore.GREEN}[AURA CORE] Dashboard opening at http://localhost:3000{Style.RESET_ALL}")
    print(f"{Fore.GREEN}[AURA CORE] Backend API at http://localhost:8000{Style.RESET_ALL}")

    # Keep the main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    boot_aura()