# install_config/install_workers/GUI/queue_handler.py

import tkinter as tk
from tkinter import messagebox, filedialog
from pathlib import Path
import sys, logging, queue, threading
from PIL import Image, ImageTk

from install_config.install_workers.GUI import widgets
from install_config.install_workers.GUI import callbacks
from install_config.install_workers import installer_steps
from install_config.install_workers.GUI.gui_setup import load_header_icon


try:
    from workers import docker_helpers
    DOCKER_HELPERS_LOADED = True
except ImportError:
    DOCKER_HELPERS_LOADED = False
    docker_helpers = None  # fallback so later code doesn't die


BDR_FOLDER_NAME = "BUILD_DEPLOY_RUN_APP"
PROJECT_ROOT = Path.cwd()
FINAL_BAT_COMMAND = f'.\\{BDR_FOLDER_NAME}\\build_and_deploy_venv_locked.bat'

log_queue = queue.Queue()
logger = logging.getLogger(__name__)

def resource_path(relative_path):
    try:
        base_path = Path(sys._MEIPASS)
    except Exception:
        base_path = Path.cwd()
    return base_path / relative_path

def get_default_docker_path():
    if DOCKER_HELPERS_LOADED:
        try:
            path = docker_helpers.get_docker_path()
            return str(path) if path else ""
        except Exception as e:
            logger.warning(f"Could not get docker path via helper: {e}")
            return ""
    return ""

def get_default_xwindows_path():
    default_path = Path("C:/Program Files/VcXsrv/vcxsrv.exe")
    if default_path.exists():
        return str(default_path)
    default_path_x86 = Path("C:/Program Files (x86)/VcXsrv/vcxsrv.exe")
    if default_path_x86.exists():
        return str(default_path_x86)
    return ""

class InstallerApp:
    def __init__(self, root):
        self.root = root
        self.root.title(f"{BDR_FOLDER_NAME} - Installer")
        self.root.geometry("700x700")
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.BDR_FOLDER_NAME = BDR_FOLDER_NAME

        load_header_icon(self)

        try:
            icon_path = Path.cwd() / "assets" / "icon.ico"
            if icon_path.is_file():
                self.root.iconbitmap(default=str(icon_path))
                logger.info(f"Window icon set from: {icon_path}")
        except Exception as e:
            logger.error(f"Failed to set window icon: {e}", exc_info=True)

        self.install_thread = None
        self.stop_event = threading.Event()
        self.current_config = {}
        self.log_queue = log_queue
        self.logging = logging
        self.messagebox = messagebox
        self.installer_steps = installer_steps
        self.PROJECT_ROOT = PROJECT_ROOT
        self.FINAL_BAT_COMMAND = FINAL_BAT_COMMAND
        self.filedialog = filedialog

        self.entrypoint_var = tk.StringVar()
        self.docker_path_var = tk.StringVar()
        self.xwindows_path_var = tk.StringVar()
        self.open_project_var = tk.BooleanVar(value=True)
        self.cli_venv_choice = tk.BooleanVar(value=False)
        self.force_replace_cli_venv = tk.BooleanVar(value=False)

        self.docker_path_var.set(get_default_docker_path())

        if not DOCKER_HELPERS_LOADED:
            self.docker_path_var.set("")  # clear it, don't trust the helper
            self.log_message("⚠️ Docker helpers unavailable. Docker integration disabled.", level=logging.WARNING)

            # If your GUI has a docker entry field, disable it to avoid user confusion
            if hasattr(self, 'docker_entry') and self.docker_entry:
                self.docker_entry.config(state=tk.DISABLED)

        self.xwindows_path_var.set(get_default_xwindows_path())

        self.png_icon = None

        class CallbacksWrapper:
            def __init__(self, app_ref): self.app = app_ref
            def browse_entrypoint(self): callbacks.browse_entrypoint(self.app)
            def browse_docker_path(self): callbacks.browse_docker_path(self.app)
            def browse_xwindows_path(self): callbacks.browse_xwindows_path(self.app)
            def on_entry_focus_in(self, event): callbacks.on_entry_focus_in(self.app, event)
            def on_entry_focus_out(self, event): callbacks.on_entry_focus_out(self.app, event)
            def copy_command(self): callbacks.copy_command(self.app)
            def copy_log_content(self): callbacks.copy_log_content(self.app)
        self.callbacks = CallbacksWrapper(self)

        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            self.bdr_source_dir = Path(sys._MEIPASS)
        else:
            self.bdr_source_dir = Path.cwd()

        try:
            widgets.setup_styles()
            widgets.create_all_widgets(self, show_venv_checkbox=True)
        except AttributeError as e:
            logger.critical(f"Fatal error creating widgets: {e}", exc_info=True)
            messagebox.showerror("Startup Error", f"Widget setup failed: {e}", parent=self.root)
            self.root.destroy()
            return

        self._start_queue_processing()

    def _start_queue_processing(self):
        def process():
            try:
                while True:
                    msg = self.log_queue.get_nowait()
                    self._write_to_log_area(msg)
            except queue.Empty:
                pass
            self.root.after(100, process)
        process()

    def _write_to_log_area(self, msg):
        if hasattr(self, 'log_area') and self.log_area:
            self.log_area.config(state=tk.NORMAL)
            self.log_area.insert(tk.END, msg + '\n')
            self.log_area.config(state=tk.DISABLED)
            self.log_area.yview(tk.END)

    def log_message(self, message, level=logging.INFO):
        if hasattr(self, 'log_queue') and self.log_queue:
            try:
                self.log_queue.put(f"[{logging.getLevelName(level)}] [GUI] {message}")
            except Exception as e:
                print(f"Error adding log to queue: {e}")

    def confirm_cli_venv_overwrite(self, path):
        if path.exists():
            return messagebox.askyesno(
                "Replace Existing Venv",
                f"An environment already exists at {path}. Replace it?",
                icon='warning', parent=self.root
            )
        return True

    def on_closing(self):
        if self.install_thread and self.install_thread.is_alive():
            if messagebox.askyesno("Exit Installer", "An installation is in progress. Are you sure you want to cancel and exit?", icon='warning'):
                self.stop_event.set()
                self.root.destroy()
        else:
            self.root.destroy()

    def on_install_complete(self):
        logger.info("Installation thread completed. Waiting for user to exit manually.")
        if hasattr(self, 'exit_button') and self.exit_button:
            try:
                self.exit_button.config(state=tk.NORMAL)
                self.log_message("Installation complete. Please click 'Exit Installer' to close.", level=logging.INFO)
            except Exception as e:
                logger.error(f"Failed to enable Exit button: {e}", exc_info=True)

    def start_installation(self):
        if self.install_thread and self.install_thread.is_alive():
            self.log_message("Installation already in progress.", level=logging.WARNING)
            return

        def run_install():
            try:
                self.installer_steps.install_project(
                    self,
                    target_project_dir=self.target_project_dir_var.get(),
                    entrypoint=self.entrypoint_var.get(),
                    docker_path=self.docker_path_var.get(),
                    xwindows_path=self.xwindows_path_var.get(),
                    skip_docker=self.skip_docker_var.get(),
                    open_paths=self.open_project_var.get(),
                    force_replace_user_venv=self.force_replace_cli_venv.get()
                )
            except Exception as e:
                logger.error(f"Installation error: {e}", exc_info=True)
                self.log_message(f"Installation failed: {e}", level=logging.ERROR)
            finally:
                self.root.after(100, self.on_install_complete)

        self.install_thread = threading.Thread(target=run_install, daemon=True)
        self.install_thread.start()
