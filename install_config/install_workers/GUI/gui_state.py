# install_config/install_workers/GUI/gui_state.py
import tkinter as tk
import logging
from pathlib import Path
import sys

logger = logging.getLogger(__name__)

class GUIStateMixin:
    """Manages GUI state variables and related logic like default paths."""

    def initialize_tk_variables(self):
        """Initialize Tkinter variables used in the GUI."""
        logger.debug("Initializing Tkinter variables...")
        self.target_project_dir_var = tk.StringVar(name="target_project_dir_var") # Give unique name
        self.entrypoint_var = tk.StringVar(name="entrypoint_var")
        self.docker_path_var = tk.StringVar(name="docker_path_var")
        self.xwindows_path_var = tk.StringVar(name="xwindows_path_var")
        self.open_project_var = tk.BooleanVar(value=True, name="open_project_var")
        self.force_replace_user_env_var = tk.BooleanVar(value=False)

        self.run_after_install_var = tk.BooleanVar(value=False, name="run_after_install_var") # Default to false

        logger.debug("Tkinter variables created.")

        # Add trace *after* root window loop starts if causes issues,
        # but usually okay here. Needs self.root though.
        # Moved trace setup to main_view after root is available.

    def set_default_paths(self):
        """Set default paths for Docker and VcXsrv if found."""
        logger.debug("Setting default paths...")
        # Default Docker Path
        default_docker_path_str = r"C:\Program Files\Docker\Docker\resources\bin\docker.exe"
        default_docker_path = Path(default_docker_path_str)
        if default_docker_path.is_file():
            self.docker_path_var.set(str(default_docker_path))
            logger.info(f"Default Docker path set to: '{default_docker_path}'")
        else:
             logger.warning(f"Default Docker path not found: '{default_docker_path_str}'")
             # Keep var empty or set placeholder if needed in entry validation
             # self.docker_path_var.set("Docker path not found - Please Browse")

        # Default Xwindows Path
        default_xwindows_path_str = r"C:\Program Files\VcXsrv\vcxsrv.exe"
        default_xwindows_path = Path(default_xwindows_path_str)
        if default_xwindows_path.is_file():
            self.xwindows_path_var.set(str(default_xwindows_path))
            logger.info(f"Default Xwindows path set to: '{default_xwindows_path}'")
        else:
            logger.warning(f"Default Xwindows path not found: '{default_xwindows_path_str}'")
            # self.xwindows_path_var.set("VcXsrv path not found - Please Browse")
        logger.debug("Default paths set attempt finished.")

    def determine_bdr_source_dir(self):
        """Determine the source directory of the BuildDeployRun tool itself."""
        logger.debug("Determining BDR source directory...")
        try:
            if getattr(sys, 'frozen', False):
                # Running as a compiled executable (PyInstaller)
                self.bdr_source_dir = Path(sys.executable).parent.resolve()
                logger.debug(f"Running as frozen, BDR Source: {self.bdr_source_dir}")
            else:
                # Running as a script
                script_dir = Path(__file__).resolve().parent # .../GUI
                install_workers_dir = script_dir.parent # .../install_workers
                install_config_dir = install_workers_dir.parent # .../install_config
                self.bdr_source_dir = install_config_dir.parent # Should be Build_Deploy_Run
                logger.debug(f"Running as script, BDR Source: {self.bdr_source_dir}")
        except Exception as e:
             logger.error(f"Error determining BDR source directory: {e}", exc_info=True)
             self.bdr_source_dir = Path.cwd() # Fallback to current working directory
             logger.warning(f"Falling back BDR source dir to CWD: {self.bdr_source_dir}")
        logger.debug("BDR Source directory determined.")

    def _on_target_project_dir_selected_trace(self, var_name, index, mode):
        """Internal trace callback. Calls the main handler."""
        # This internal method handles the trace specifics
        self.handle_target_project_dir_change()

    def handle_target_project_dir_change(self):
        """Handles logic when the target project directory changes."""
        target_dir = self.target_project_dir_var.get()
        is_valid_dir = target_dir and Path(target_dir).is_dir()
        entrypoint_widgets_state = tk.NORMAL if is_valid_dir else tk.DISABLED

        entrypoint_entry = getattr(self, 'entrypoint_entry', None)
        entrypoint_browse_button = getattr(self, 'entrypoint_browse_button', None)

        # Enable/disable Entrypoint Entry widget
        if entrypoint_entry:
            entrypoint_entry.config(state=entrypoint_widgets_state)
            # Clear/reset placeholder if directory becomes invalid or is cleared
            if not is_valid_dir:
                self.entrypoint_var.set('')
                placeholder = getattr(self, 'entrypoint_placeholder', '')
                if placeholder:
                     # Temporarily enable to modify content
                    current_state = entrypoint_entry.cget('state')
                    entrypoint_entry.config(state=tk.NORMAL)
                    entrypoint_entry.delete(0, tk.END)
                    entrypoint_entry.insert(0, placeholder)
                    entrypoint_entry.config(foreground='grey')
                    entrypoint_entry.config(state=current_state) # Restore original state (likely DISABLED)


        # Enable/disable Entrypoint Browse button
        if entrypoint_browse_button:
            entrypoint_browse_button.config(state=entrypoint_widgets_state)

        if is_valid_dir:
            logger.info(f"Target project directory set: '{target_dir}'. Entrypoint enabled.")
        else:
            logger.warning(f"Target project directory cleared or invalid: '{target_dir}'. Entrypoint disabled.")