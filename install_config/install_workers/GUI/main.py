# install_config/install_workers/GUI/main.py

import tkinter as tk
import queue
import logging
from pathlib import Path
from install_config.install_workers.GUI.main_view import InstallerApp

# Optional: Tweak logging level to debug GUI behavior
logging.basicConfig(level=logging.INFO)

def launch_gui(config_constants):
    # import queue # No need to re-import if done globally
    log_q = queue.Queue()
    root = tk.Tk()
    app = InstallerApp(root, config_constants, log_q) # Instantiation should be fine
    root.mainloop()

if __name__ == "__main__":
    config_constants = {
        "BDR_FOLDER_NAME": "Build_Deploy_Run",
        "PROJECT_ROOT": str(Path.cwd()),
        "FINAL_BAT_COMMAND": r".\Build_Deploy_Run\build_and_deploy_venv_locked.bat"
    }
    launch_gui(config_constants)

