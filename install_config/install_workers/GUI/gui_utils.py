# install_config/install_workers/GUI/gui_utils.py

import subprocess, queue, logging, json, os, sys
from pathlib import Path
import tkinter as tk
from PIL import Image, ImageTk

logger = logging.getLogger(__name__)

def get_resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller frozen .exe """
    try:
        base_path = sys._MEIPASS  # PyInstaller sets this when frozen
        logger.debug(f"Using _MEIPASS as base_path: {base_path}")
    except AttributeError:
        base_path = os.path.abspath(".")
        logger.debug(f"Using current directory as base_path: {base_path}")
    resource_path = os.path.join(base_path, relative_path)
    logger.debug(f"Resolved resource path for '{relative_path}': {resource_path}")
    return resource_path


def get_icon_image(relative_path: str, size=(64, 64)):
    """
    Safely load a Tkinter-compatible image (e.g., PNG).
    - Uses get_resource_path to handle PyInstaller bundling.
    - If file is missing, logs a warning and returns None.
    """
    try:
        # Use get_resource_path to get the absolute path to the bundled resource
        absolute_path = get_resource_path(relative_path)
        img = Image.open(absolute_path)
        resized = img.resize(size, Image.Resampling.LANCZOS)
        return ImageTk.PhotoImage(resized)
    except Exception as e:
        logging.getLogger(__name__).warning(f"Failed to load icon from {relative_path}: {e}")
        return None


def log_to_queue(queue_obj, message, level=logging.INFO):
    """
    Enqueues a standardized (level, message) tuple for log processing.
    """
    try:
        queue_obj.put_nowait((level, str(message)))
    except Exception as e:
        logger.error(f"[QueueLogError] Failed to enqueue log: {e}")


def write_deploy_config(app_instance):
    """
    Write a deploy_config.json file into the user's project directory.
    Pulls paths and settings from app_instance variables.
    """
    try:
        target_path = Path(app_instance.target_project_dir_var.get())
        # Assuming config goes inside the BDR folder in target project
        config_path = target_path / "Build_Deploy_Run" / "deploy_config.json"

        deploy_config = {
            "entrypoint": app_instance.entrypoint_var.get(),
            "docker_path": app_instance.docker_path_var.get(),
            "xwindows_path": app_instance.xwindows_path_var.get(),
            "open_project": app_instance.open_project_var.get(),
        }

        # Ensure the target directory exists
        config_path.parent.mkdir(parents=True, exist_ok=True)

        with open(config_path, 'w') as f:
            json.dump(deploy_config, f, indent=4)

        app_instance.log_message_action(f"[CONFIG] deploy_config.json written to: {config_path}", logging.INFO)

    except Exception as e:
        app_instance.log_message_action(f"[ERROR] Could not write deploy_config.json: {e}", logging.ERROR)
        logger.exception("Exception while writing deploy_config.json")


LEVEL_STYLES = {
    logging.DEBUG:    ("gray", "[debug]"),
    logging.INFO:     ("black", "[info] "),
    logging.WARNING:  ("orange", "[warn] "),
    logging.ERROR:    ("red", "[ERROR]"),
    logging.CRITICAL: ("dark red", "[FATAL]"),
}


def log_message(app, message, level=logging.INFO):
    """Appends a line to the GUI log area. ASCII prefixes only: the console may be cp1252."""
    tag_color, prefix = LEVEL_STYLES.get(level, ("black", "[info] "))
    full_message = f"{prefix} {str(message).strip()}\n"

    log_area = getattr(app, "log_area", None)
    if log_area is None:
        print(full_message, end="")
        return

    try:
        log_area.configure(state=tk.NORMAL)
        if "dark red" not in log_area.tag_names():
            for color in ("gray", "black", "orange", "red", "dark red"):
                log_area.tag_config(color, foreground=color)
        log_area.insert(tk.END, full_message, (tag_color,))
        log_area.see(tk.END)
    except Exception as e:
        logger.error(f"log_message: could not update log widget: {e}")
    finally:
        try:
            log_area.configure(state=tk.DISABLED)
        except Exception:
            pass


def start_queue_processing(app):
    """Polls app.log_queue every 100 ms and writes entries to the log area."""

    def poll_log_queue():
        root = getattr(app, "root", None)
        try:
            if root is None or not root.winfo_exists():
                return
        except Exception:
            return

        while True:
            try:
                data = app.log_queue.get_nowait()
            except queue.Empty:
                break
            try:
                if isinstance(data, tuple) and len(data) == 2:
                    level, msg = data
                elif isinstance(data, tuple) and len(data) == 3:
                    level, _tag, msg = data
                else:
                    level, msg = logging.INFO, str(data)
                log_message(app, msg, level)
            except Exception as e:
                logger.error(f"Log queue processing error: {e}", exc_info=True)

        try:
            root.after(100, poll_log_queue)
        except Exception as e:
            logger.debug(f"poll_log_queue reschedule failed (shutting down?): {e}")

    poll_log_queue()


# FIX: Ensure this function definition starts at column 0 (no indentation)
def run_subprocess_streamed(cmd, queue_obj, cwd=None, env=None):
    """Runs subprocess, streams stdout/stderr to queue."""
    try:
        process = subprocess.Popen(
            cmd,
            cwd=cwd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, # Redirect stderr to stdout
            text=True,
            bufsize=1, # Line buffered
            encoding='utf-8', # Be explicit about encoding
            errors='replace'  # Handle potential decoding errors
        )
        # Log stdout line by line
        for line in process.stdout:
            log_to_queue(queue_obj, line.strip(), logging.INFO) # Pass level INFO

        process.wait() # Wait for process to complete
        if process.returncode != 0:
            # Log error with return code if process failed
            error_message = f"Subprocess failed with return code {process.returncode}: {' '.join(cmd)}"
            log_to_queue(queue_obj, error_message, logging.ERROR) # Pass level ERROR
            raise subprocess.CalledProcessError(process.returncode, cmd)

    except FileNotFoundError:
         error_message = f"Command not found: {cmd[0]}"
         log_to_queue(queue_obj, error_message, logging.CRITICAL)
         raise # Re-raise the exception
    except Exception as e:
         error_message = f"Error running subprocess {cmd[0]}: {e}"
         log_to_queue(queue_obj, error_message, logging.CRITICAL)
         raise # Re-raise the exception