# install_config/install_workers/install_core.py

import logging, shutil, sys
import pyperclip
import tkinter as tk
from pathlib import Path

from install_config.install_workers import venv_utils, installer_steps
from install_config.install_workers.deploy_config import generate_deploy_config

logger = logging.getLogger(__name__)

def prevent_auto_exit(app_instance):
    """
    After install finishes, disables the automatic exit
    and instead enables an "Exit Installer" button manually.
    """
    logger.debug("Applying prevent_auto_exit patch...")

    try:
        if hasattr(app_instance, 'exit_button') and app_instance.exit_button:
            def unlock_exit():
                app_instance.exit_button.config(state=tk.NORMAL)
                logger.info("Exit button enabled. Waiting for user to close manually.")

            app_instance.root.after(100, unlock_exit)
        else:
            logger.warning("No 'exit_button' found to enable after install.")
    except Exception as e:
        logger.error(f"Failed to apply prevent_auto_exit patch: {e}", exc_info=True)

def install_project(app,
                    target_project_dir: Path,
                    entrypoint: str,
                    docker_path: str,
                    xwindows_path: str,
                    skip_docker: bool,
                    open_paths: bool,
                    force_replace_user_venv: bool = False):
    """ Full installation logic controller """
    logger.info(f"Starting installation for project: {target_project_dir}")

    # Step 1: Copy BDR Scripts
    bdr_folder = target_project_dir / "Build_Deploy_Run"
    if bdr_folder.exists():
        logger.warning(f"[BDR] Overwriting existing contents of: {bdr_folder}")
        shutil.rmtree(bdr_folder)
    shutil.copytree(Path(sys._MEIPASS, "Build_Deploy_Run"), bdr_folder)

    # Step 2: Create Internal venv
    internal_venv_path = bdr_folder / ".venv"
    venv_utils.create_venv(internal_venv_path)

    # Step 3: Install Requirements into BDR venv
    installer_steps.install_requirements(internal_venv_path, skip_docker=skip_docker)

    # Step 4: Manage User venv
    installer_steps.handle_user_project_venv(
        target_project_dir=target_project_dir,
        force_replace=force_replace_user_venv
    )

    # Step 5: Save deploy metadata and clipboard launch
    generate_deploy_config(
        target_project_dir=target_project_dir,
        entrypoint=entrypoint,
        docker_path=docker_path,
        xwindows_path=xwindows_path,
        open_project=open_paths
    )

    bat_cmd = f".\\Build_Deploy_Run\\build_and_deploy_venv_locked.bat"
    pyperclip.copy(bat_cmd)
    logger.info("[CLIPBOARD] Launch command copied to clipboard.")
    logger.info("[INSTALL COMPLETE] Installation finished successfully. Venv exited.")

    try:
        prevent_auto_exit(app)
    except Exception as e:
        logger.warning(f"Failed to apply GUI exit patch: {e}")
