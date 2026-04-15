# launch_gui.py
import tkinter as tk
from install_config.install_workers.GUI.main_view import InstallerApp
import queue
import logging

if __name__ == "__main__":
    # Optional: configure logging before GUI starts
    logging.basicConfig(level=logging.DEBUG)

    # Create the main Tkinter root window
    root = tk.Tk()

    # Define any necessary config constants to pass
    config_constants = {
        "BDR_FOLDER_NAME": "Build_Deploy_Run",
        "PROJECT_ROOT": ".",  # Current working directory or customize
        "FINAL_BAT_COMMAND": r".\Build_Deploy_Run\build_and_deploy_venv_locked.bat"
    }

    # Queue to send logs to GUI
    gui_log_queue = queue.Queue()

    # Start the Installer GUI app
    app = InstallerApp(root, config_constants, gui_log_queue)
    root.mainloop()
