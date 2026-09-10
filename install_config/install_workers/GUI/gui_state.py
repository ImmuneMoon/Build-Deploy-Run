# install_config/install_workers/GUI/gui_state.py
import tkinter as tk
import logging
import os
from pathlib import Path

from install_config.install_workers.install_utils import get_bdr_source_dir

logger = logging.getLogger(__name__)


class GUIStateMixin:
    """Manages GUI state variables and related logic like default paths."""

    def initialize_tk_variables(self):
        """Initialize Tkinter variables used in the GUI."""
        logger.debug("Initializing Tkinter variables...")
        self.target_project_dir_var = tk.StringVar(name="target_project_dir_var")
        self.entrypoint_var = tk.StringVar(name="entrypoint_var")
        self.docker_path_var = tk.StringVar(name="docker_path_var")
        self.xwindows_path_var = tk.StringVar(name="xwindows_path_var")
        self.open_project_var = tk.BooleanVar(value=True, name="open_project_var")
        self.force_replace_user_env_var = tk.BooleanVar(value=False, name="force_replace_user_env_var")
        # "both" | "exe" | "docker"
        self.build_target_var = tk.StringVar(value="both", name="build_target_var")
        self.run_after_install_var = tk.BooleanVar(value=True, name="run_after_install_var")
        logger.debug("Tkinter variables created.")

    def set_default_paths(self):
        """Set default paths for Docker and VcXsrv if found."""
        logger.debug("Setting default paths...")
        docker_candidates = [
            Path(r"C:\Program Files\Docker\Docker\resources\bin\docker.exe"),                      # machine-wide
            Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "DockerDesktop" / "resources" / "bin" / "docker.exe",  # per-user
        ]
        default_docker_path = next((p for p in docker_candidates if p.is_file()), None)
        if default_docker_path:
            self.docker_path_var.set(str(default_docker_path))
            logger.info(f"Default Docker path set to: '{default_docker_path}'")
        else:
            logger.warning("Docker Desktop not found in the default machine-wide or per-user locations.")
            # Docker is optional: an empty field means "look it up on PATH at build time".
            logger.info("Docker Desktop not found at the default location; a Docker build will look for 'docker' on PATH.")

        default_xwindows_path = Path(r"C:\Program Files\VcXsrv\vcxsrv.exe")
        if default_xwindows_path.is_file():
            self.xwindows_path_var.set(str(default_xwindows_path))
            logger.info(f"Default Xwindows path set to: '{default_xwindows_path}'")
        else:
            logger.warning(f"Default Xwindows path not found: '{default_xwindows_path}'")
        logger.debug("Default paths set attempt finished.")

    def determine_bdr_source_dir(self):
        """Determine the source directory of the BuildDeployRun tool itself."""
        try:
            self.bdr_source_dir = get_bdr_source_dir()
            logger.debug(f"BDR Source: {self.bdr_source_dir}")
        except Exception as e:
            logger.error(f"Error determining BDR source directory: {e}", exc_info=True)
            self.bdr_source_dir = Path.cwd()
            logger.warning(f"Falling back BDR source dir to CWD: {self.bdr_source_dir}")

    def _on_target_project_dir_selected_trace(self, var_name, index, mode):
        self.handle_target_project_dir_change()

    def handle_target_project_dir_change(self):
        """Enables the entrypoint widgets once a valid project directory is chosen."""
        target_dir = self.target_project_dir_var.get()
        is_valid_dir = bool(target_dir) and Path(target_dir).is_dir()
        entrypoint_widgets_state = tk.NORMAL if is_valid_dir else tk.DISABLED

        entrypoint_entry = getattr(self, "entrypoint_entry", None)
        entrypoint_browse_button = getattr(self, "entrypoint_browse_button", None)

        if entrypoint_entry:
            entrypoint_entry.config(state=entrypoint_widgets_state)
            if not is_valid_dir:
                self.entrypoint_var.set("")
                placeholder = getattr(self, "entrypoint_placeholder", "")
                if placeholder:
                    current_state = entrypoint_entry.cget("state")
                    entrypoint_entry.config(state=tk.NORMAL)
                    entrypoint_entry.delete(0, tk.END)
                    entrypoint_entry.insert(0, placeholder)
                    entrypoint_entry.config(foreground="grey")
                    entrypoint_entry.config(state=current_state)

        if entrypoint_browse_button:
            entrypoint_browse_button.config(state=entrypoint_widgets_state)

        if is_valid_dir:
            logger.info(f"Target project directory set: '{target_dir}'. Entrypoint enabled.")
        else:
            logger.warning(f"Target project directory cleared or invalid: '{target_dir}'. Entrypoint disabled.")
