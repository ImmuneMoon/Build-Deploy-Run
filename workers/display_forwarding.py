# workers/ display_forwarding.py

import subprocess
import time
from pathlib import Path
try:
    from colorama import Fore, Style, init
    init(autoreset=True)
except ImportError:
    class Dummy:
        def __getattr__(self, attr): return ''
    Fore = Style = Dummy()
    def init(*args, **kwargs): pass



def launch_vcxsrv(vcxsrv_path: Path):
    """
    Attempts to launch VcXsrv with sane defaults.
    """
    if not vcxsrv_path.exists():
        print(Fore.RED + f"[X] VcXsrv not found at: {vcxsrv_path}")
        return False

    print(Fore.YELLOW + f"[*] Launching VcXsrv from: {vcxsrv_path}")
    try:
        subprocess.Popen([
            str(vcxsrv_path),
            ":0",
            "-multiwindow",
            "-clipboard",
            "-wgl",
            "-ac"
        ])
        time.sleep(3)
        print(Fore.GREEN + "[✓] VcXsrv launched.")
        return True
    except Exception as e:
        print(Fore.RED + f"[X] Failed to launch VcXsrv: {e}")
        return False


def minimize_x_windows(minimizer_script: Path):
    """
    Executes a PowerShell script to minimize X windows.
    """
    if not minimizer_script.exists():
        print(Fore.YELLOW + "[!] Minimize script not found.")
        return

    print(Fore.YELLOW + "[*] Minimizing VcXsrv window...")
    try:
        subprocess.run([
            "powershell",
            "-ExecutionPolicy", "Bypass",
            "-File", str(minimizer_script)
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(Fore.GREEN + "[✓] VcXsrv window minimized.")
    except Exception as e:
        print(Fore.RED + f"[X] Failed to minimize X windows: {e}")
