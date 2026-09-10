# install_config/install_workers/GUI/main_view.py
# Contains the main InstallerApp class shell

import tkinter as tk
from tkinter import messagebox, filedialog
import logging, threading, queue, sys, subprocess
from pathlib import Path
# Keep pyperclip fallback if used
try:
    import pyperclip
    PYPERCLIP_AVAILABLE = True
except ImportError:
    PYPERCLIP_AVAILABLE = False

try:
    from plyer import notification
    PLYER_AVAILABLE = True
except ImportError:
    notification = None # Set to None if plyer is not installed
    PLYER_AVAILABLE = False
    logging.warning("Plyer library not found, desktop notifications disabled. Run 'pip install plyer'.")


from install_config.install_workers.GUI import gui_setup, gui_utils
from install_config.install_workers.GUI.gui_state import GUIStateMixin
from install_config.install_workers import installer_steps
from install_config.install_workers.GUI.gui_actions import notify_command_ready


logger = logging.getLogger(__name__)



def _send_notification(title, message):
    """Safely sends a notification if plyer is available."""
    if notification and PLYER_AVAILABLE:
        try:
            notification.notify(
                title=title,
                message=message,
                app_name="Build Deploy Run",
                timeout=10
            )
            logger.info(f"Sent notification: Title='{title}'")
        except NotImplementedError:
            logger.warning("Notification backend not available. Skipping.")

    else:
        logger.debug("Plyer not available, skipping notification.")



class InstallerApp(GUIStateMixin):
    """Main class for the Installer GUI application."""

    def __init__(self, root: tk.Tk, config_constants: dict, log_to_queue: queue.Queue):
        logger.debug("Initializing InstallerApp instance...")
        self.root = root

        try:
            # --- Core App Setup ---
            self.log_queue = log_to_queue
            self.config_constants = config_constants
            self.BDR_FOLDER_NAME = config_constants.get('BDR_FOLDER_NAME', 'Build_Deploy_Run') # Default name
            self.PROJECT_ROOT = config_constants.get('PROJECT_ROOT') # Project where BDR is run FROM (dev)
            self.FINAL_BAT_COMMAND = config_constants.get('FINAL_BAT_COMMAND') # Command shown to user
            self.is_installing = False
            self.install_thread = None
            self.stop_event = threading.Event()
            # self.current_config = {} # No longer needed here, built in start_installation_action

            # --- GUI State Variables (Initialized via Mixin) ---
            self.target_project_dir_var = None
            self.entrypoint_var = None
            self.docker_path_var = None
            self.xwindows_path_var = None
            self.open_project_var = None
            self.force_replace_user_env_var = None # Expected from mixin/gui_state.py
            self.build_target_var = None           # Created in initialize_tk_variables (do not create twice:
            self.run_after_install_var = None      # a discarded named tk.Variable deletes the Tcl variable)

            # --- GUI Widget References (Populated by gui_setup) ---
            self.png_icon = None
            self.icon_display_size = (48, 48) # Default icon size
            self.callbacks = None # Wrapper set by gui_setup
            self.bdr_source_dir = None # Determined by determine_bdr_source_dir
            self.entrypoint_placeholder = "e.g., main.py"
            self.target_project_dir_entry = None
            self.target_project_browse_button = None
            self.entrypoint_entry = None
            self.entrypoint_browse_button = None
            self.docker_path_entry = None
            self.xwindows_path_entry = None
            self.log_area = None
            self.progress = None
            self.final_frame = None
            self.command_entry = None
            self.copy_button = None
            self.install_button = None
            self.exit_button = None
            self.run_after_checkbox = None # Optional widget reference
            self.save_config_button = None # Optional widget reference
            self.force_replace_checkbox = None # Reference for the new checkbox

            # --- System Modules ---
            self.messagebox = messagebox
            self.filedialog = filedialog

            # --- Initialization Steps ---
            self.root.title("Build Deploy Run")
            self.root.geometry("700x650") # Adjust size as needed

            self.determine_bdr_source_dir()   # Determine where BDR source files are
            self.initialize_tk_variables()    # Initialize all tk.StringVar/BooleanVar etc.
            self.set_default_paths()          # Set default Docker/Xwindows paths

            gui_setup.setup_window_icon(self)       # Set window icon
            gui_setup.load_header_icon(self)        # Load header PNG
            gui_setup.setup_callbacks_wrapper(self) # Attach callback functions
            gui_setup.setup_ui_widgets(self)        # Create all widgets

            # Add trace *after* widgets are created if callbacks need widget refs
            if self.target_project_dir_var:
                self.target_project_dir_var.trace_add("write", self._on_target_project_dir_selected_trace)
                self.handle_target_project_dir_change() # Initial check for enabling entrypoint
            else:
                logger.error("target_project_dir_var was not initialized correctly.")

            self.root.protocol("WM_DELETE_WINDOW", self.on_closing) # Handle window close
            gui_utils.start_queue_processing(self) # Start polling log queue

            self.log_message_action("Build Deploy Run ready. Pick a project folder and an entrypoint, then click Build Project.", logging.INFO)
            self.log_message_action(f"Build tools source: {self.bdr_source_dir}", logging.DEBUG)
            logger.debug("InstallerApp - Initialization complete.")

        except Exception as e:
            # Catch any critical error during initialization
            logger.critical(f"FATAL ERROR during InstallerApp.__init__: {e}", exc_info=True)
            try: # Try to show error popup
                messagebox.showerror("Initialization Error", f"A critical error occurred during startup:\n{e}")
            except Exception as e_msg:
                print(f"FATAL ERROR in __init__, cannot show messagebox: {e_msg}")
            # Attempt to close window cleanly if possible
            if hasattr(self, 'root') and self.root:
                try: self.root.destroy()
                except: pass
            sys.exit(f"FATAL ERROR in InstallerApp __init__")


    def log_message_action(self, message, level=logging.INFO):
        """Safely logs messages to both queue and logger."""
        # Ensure message is string
        message_str = str(message)
        # Log to main logger
        logger.log(level, message_str)
        # Log to GUI via queue
        if hasattr(self, 'log_queue') and self.log_queue:
            gui_utils.log_to_queue(self.log_queue, message_str, level)
        else:
            # Fallback if queue isn't ready yet during init
            print(f"[LOG FALLBACK] {logging.getLevelName(level)}: {message_str}")


    def on_closing(self):
        """Handles window close event (WM_DELETE_WINDOW protocol)."""
        self._handle_closing_internal()


    def _handle_closing_internal(self):
        """Internal logic for closing the application."""
        logger.info("Exit requested...")
        if self.install_thread and self.install_thread.is_alive():
            if messagebox.askyesno("Confirm Exit", "A build is running. Cancel and exit?", parent=self.root, icon='warning'):
                self.stop_event.set() # Signal thread to stop
                self.is_installing = False # Update state
                self.log_message_action("Cancellation requested by user.", logging.WARNING)
                # Give thread a moment to potentially stop gracefully? Maybe not needed.
                try:
                    if self.root and self.root.winfo_exists(): self.root.destroy()
                except Exception as e: logger.error(f"Error destroying root window: {e}")
            else:
                logger.debug("Exit cancelled by user.")
                return # Don't close if user cancels
        else:
            # No install running, just close
            self.is_installing = False
            try:
                if self.root and self.root.winfo_exists(): self.root.destroy()
            except Exception as e: logger.error(f"Error destroying root window: {e}")


# determine_bdr_source_dir from GUIStateMixin
    def field_value(self, var_name: str) -> str:
        """Returns the stripped value of a StringVar, or '' if it still shows its placeholder text."""
        var = getattr(self, var_name, None)
        if var is None:
            return ""
        value = var.get().strip()
        placeholder = getattr(self, "placeholders", {}).get(var_name)
        return "" if placeholder and value == placeholder else value

    def validate_critical_paths(self):
        """Ensure all critical paths (docker, xwindows) are valid if specified."""
        errors = []

        # Both fields are optional: empty means "not configured" and must not block the install.
        docker_path = self.field_value("docker_path_var")
        xwindows_path = self.field_value("xwindows_path_var")

        if docker_path and not Path(docker_path).is_file():
            errors.append(f"Docker executable not found at: {docker_path}")

        if xwindows_path and not Path(xwindows_path).is_file():
            errors.append(f"VcXsrv (xwindows) executable not found at: {xwindows_path}")

        if errors:
            messagebox.showerror("Invalid Paths", "\n".join(errors))
            return False

        return True


    def on_install_button_click(self):
        """Callback for the 'Start Installation' button."""
        self.start_installation_action()


    def start_installation_action(self):
        """
        Validates inputs and initiates the installation process in a separate thread.
        Passes necessary configuration (entrypoint, paths, flags) to the installer steps.
        """

        if not self.validate_critical_paths():
            return  # Abort if invalid paths found

        if self.is_installing:
            self.log_message_action("A build is already in progress.", logging.WARNING)
            return

        # --- Get values from GUI ---
        target_dir = self.field_value("target_project_dir_var")
        entrypoint_value = self.field_value("entrypoint_var")
        docker_path_value = self.field_value("docker_path_var")
        xwindows_path_value = self.field_value("xwindows_path_var")
        open_project_flag = self.open_project_var.get()

        # Safely get boolean flags, default to False if var not found
        force_replace_flag = False # Default value
        if hasattr(self, 'force_replace_user_env_var'):
            try:
                # Try getting the value from the Tkinter variable
                force_replace_flag = getattr(self.force_replace_user_env_var, "get", lambda: False)()
                logger.debug(f"Successfully retrieved force_replace_user_env_var value: {force_replace_flag}") # Add debug log
            except tk.TclError as e:
                # Log if a specific Tkinter error occurs during .get()
                logger.warning(f"TclError getting force_replace_user_env_var: {e}. Defaulting to False.")
            except Exception as e_other:
                # Log any other unexpected errors during .get()
                logger.error(f"Unexpected error getting force_replace_user_env_var: {e_other}. Defaulting to False.", exc_info=True)
        else:
            # This case should ideally not happen if initialization is correct
            logger.error("Attribute 'force_replace_user_env_var' missing during get. Defaulting to False.")

        try:
            build_target = self.build_target_var.get()
        except (AttributeError, tk.TclError):
            build_target = "both"
        skip_docker_flag = build_target == "exe"
        skip_exe_flag = build_target == "docker"
        try:
            run_after_flag = self.run_after_install_var.get()
        except (AttributeError, tk.TclError):
            run_after_flag = True

        placeholder = getattr(self, 'entrypoint_placeholder', 'e.g., main.py')

        # --- Input Validation ---
        if not target_dir or not Path(target_dir).is_dir():
            self.messagebox.showerror("Input Error", "Please select a valid project directory.", parent=self.root)
            self.log_message_action("Validation failed: Invalid target project directory.", logging.ERROR)
            return

        entrypoint_path = Path(target_dir) / entrypoint_value
        if not entrypoint_value or entrypoint_value == placeholder or not entrypoint_path.is_file():
            self.messagebox.showerror("Input Error", f"Please select a valid entrypoint script within the project directory.\nChecked: {entrypoint_path}", parent=self.root)
            self.log_message_action(f"Validation failed: Invalid entrypoint script '{entrypoint_value}'.", logging.ERROR)
            return

        # --- Prepare for Installation ---
        self.is_installing = True
        # Update GUI state (disable buttons, start progress)
        if self.install_button: self.install_button.config(state=tk.DISABLED)
        if self.exit_button: self.exit_button.config(text="Cancel") # Change text to indicate cancel action
        if self.progress:
            self.progress.start(10) # Start indeterminate progress
        if self.final_frame:
            self.final_frame.grid_remove() # Ensure final frame is hidden

        # Define paths
        user_project_path = Path(target_dir)
        # Get BDR source dir determined at init
        bdr_source_dir_path = self.bdr_source_dir

        # Log configuration being used
        self.log_message_action(f"Starting build for project: {user_project_path}", logging.INFO)
        self.log_message_action(f"  BDR Source: {bdr_source_dir_path}", logging.DEBUG)
        self.log_message_action(f"  Entrypoint: {entrypoint_value}", logging.INFO)
        self.log_message_action(f"  Force Replace User Venv: {force_replace_flag}", logging.INFO)
        self.log_message_action(f"  Open Project Folder: {open_project_flag}", logging.INFO)
        self.log_message_action(f"  Docker Path: {docker_path_value or 'Not Set'}", logging.INFO)
        self.log_message_action(f"  Xwindows Path: {xwindows_path_value or 'Not Set'}", logging.INFO)
        self.log_message_action(f"  Build target: {build_target}", logging.INFO)
        self.log_message_action(f"  Run build after install: {run_after_flag}", logging.INFO)

        self.install_result = None

        # --- Run Installation in Thread ---
        def run_install():
            """Target function for the installation thread."""
            install_success = False
            try:
                # Call prepare_and_run_installation from installer_steps
                # Pass all necessary arguments obtained from the GUI state
                install_success = installer_steps.prepare_and_run_installation(
                    source_dir=bdr_source_dir_path,         # Source of BDR files
                    user_project_dir=user_project_path,     # Target project dir
                    entrypoint=entrypoint_value,            # User selected entrypoint
                    force_replace_user_env=force_replace_flag, # Checkbox value
                    open_project=open_project_flag,
                    docker_path=docker_path_value,          # Docker path from GUI
                    xwindows_path=xwindows_path_value,      # Xwindows path from GUI
                    log_queue=self.log_queue,               # For logging from thread
                    stop_event=self.stop_event,             # For cancellation
                    skip_docker=skip_docker_flag,           # Pass skip docker flag
                    skip_exe=skip_exe_flag,
                    run_after_install=run_after_flag,
                )
            except Exception as e:
                # Catch unexpected errors within the thread itself
                error_msg = f"Build thread crashed: {e}"
                self.log_message_action(error_msg, logging.CRITICAL)
                logger.error(f"Installation thread exception: {e}", exc_info=True)
                # Log to queue to ensure GUI gets notified if possible
                _send_notification("Build Failed", f"{type(e).__name__}: {e}")

                try:
                    self.log_queue.put((logging.CRITICAL, f"FATAL INSTALL ERROR: {e}"))
                except Exception: pass # Ignore queue errors if GUI is closing
            finally:
                # Log thread completion status; _check_install_complete reads install_result.
                self.install_result = bool(install_success)
                logger.debug(f"Installation thread finished. Reported Success={install_success}")

        # Create and start the thread
        self.stop_event.clear() # Ensure stop event is clear before starting
        self.install_thread = threading.Thread(target=run_install, daemon=True)
        self.install_thread.start()
        logger.debug("Installation thread started.")

        # Start polling to check when the thread finishes
        self.root.after(500, self._check_install_complete) # Check status after 0.5 seconds


    def _check_install_complete(self):
        """Polls the installation thread and updates GUI on completion/cancellation."""
        if not self.is_installing:
            # Installation was cancelled or finished, but poll might run one last time
            logger.debug("Install complete check called, but not installing. Stopping poll.")
            return

        if self.install_thread and not self.install_thread.is_alive():
            logger.info("Installation thread has finished.")
            self.is_installing = False
            # Stop progress bar
            if self.progress:
                self.progress.stop()
                self.progress['value'] = 100 # Indicate completion (or reset)
            # Reset buttons
            if self.exit_button: self.exit_button.config(text="Exit")
            if self.install_button: self.install_button.config(state=tk.NORMAL)

            # Check if cancellation was requested
            if self.stop_event.is_set():
                 self.log_message_action("Build was cancelled.", logging.WARNING)
                 # show a messagebox for cancellation
                 self.messagebox.showwarning("Cancelled", "Build cancelled.", parent=self.root)
                 # Send notification of cancellation if user minimizes window
                 _send_notification("Build Cancelled", "User aborted the process.")

            elif getattr(self, "install_result", False):
                 self.log_message_action("Build completed successfully.", logging.INFO)
                 _send_notification("Build Deploy Run", "Build complete. Output is in your project's dist folder.")
                 self.show_final_cli_command() # Shows the rebuild command and copies it
            else:
                 self.log_message_action("Build FAILED. See the log above for the failing step.", logging.ERROR)
                 self.messagebox.showerror(
                     "Build Failed",
                     "The build did not complete.\n\nCheck the Build Log for the step marked FAILED "
                     "(right-click the log to copy it).",
                     parent=self.root)
                 _send_notification("Build Deploy Run", "Build failed. See the log for details.")

        else:
            # If still running, schedule the next check
            logger.debug("Install thread still running, rescheduling check.")
            self.root.after(1000, self._check_install_complete) # Check again in 1 second


    def show_final_cli_command(self):
        """Displays the final command frame and copies command."""
        command = self.FINAL_BAT_COMMAND or r".\Build_Deploy_Run\build_and_deploy_venv_locked.bat" # Use raw string
        logger.info(f"Showing final command frame. Command: {command}")
        if self.final_frame:
             if self.command_entry:
                 self.command_entry.config(state=tk.NORMAL)
                 self.command_entry.delete(0, tk.END)
                 self.command_entry.insert(0, command)
                 self.command_entry.config(state='readonly')
             if self.copy_button:
                 self.copy_button.config(state=tk.NORMAL) # Enable copy button
             self.final_frame.grid() # Make frame visible
             # Attempt to copy to clipboard
             try:
                 # Use built-in clipboard methods if available
                 self.root.clipboard_clear()
                 self.root.clipboard_append(command)
                 self.root.update() # Essential on some systems
                 self.log_message_action("Command copied to clipboard.", logging.INFO)
                 notify_command_ready(self)
             except tk.TclError as e:
                  logger.warning(f"Tkinter clipboard failed: {e}. Trying pyperclip...")
                  if PYPERCLIP_AVAILABLE:
                      try:
                          pyperclip.copy(command)
                          self.log_message_action("Command copied using pyperclip.", logging.INFO)
                      except Exception as pe:
                          logger.error(f"Pyperclip fallback failed: {pe}")
                          self.log_message_action("Failed to copy command to clipboard.", logging.ERROR)
                  else:
                      self.log_message_action("Pyperclip not available. Failed to copy command.", logging.ERROR)
             except Exception as clip_e:
                  logger.error(f"Unexpected clipboard error: {clip_e}")
                  self.log_message_action("Failed to copy command to clipboard.", logging.ERROR)

        else:
            logger.error("Final command frame widget not found!")


    def reset_after_failure(self):
        """Resets the GUI state after a failed installation attempt."""
        logger.warning("Resetting GUI after installation failure.")
        self.is_installing = False
        if self.install_button: self.install_button.config(state=tk.NORMAL)
        if self.exit_button: self.exit_button.config(text="Exit")
        if self.progress: self.progress.stop()

# Note: GUIStateMixin methods like initialize_tk_variables, set_default_paths etc.
# should be defined in gui_state.py and inherited here.