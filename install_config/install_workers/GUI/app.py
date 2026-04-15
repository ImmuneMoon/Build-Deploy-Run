# install_config/install_workers/app.py
import logging
import time
from pathlib import Path
import threading
from install_config.install_workers.venv_utils import create_venv
from install_config.install_workers.GUI.gui_utils import log_to_queue
from install_config.install_workers.installer_steps import prepare_and_run_installation
# Core installer logic
from install_config.install_workers.install_core import (
    run_installation,
    install_requirements,

)
from install_config.install_workers.install_utils import copy_bdr_scripts


logger = logging.getLogger(__name__)

# --- Utility Decorator ---
# Times each step for diagnostics and logging.
def time_wrapper(func):
    def wrapped(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        elapsed = time.time() - start
        logger.info(f"[STEP TIMER] {func.__name__} completed in {elapsed:.2f}s")
        return result
    return wrapped

# --- Step Builder ---
def build_steps(source_dir, user_project_dir, bdr_env_path, bdr_requirements_path):
    """
    Dynamically builds the list of steps the installer should run.
    This structure is consumed by run_installation().
    """
    steps = []

    # Step 1: Copy all required deployment files (if missing, raise)
    steps.append({
        'name': 'Copy BDR Scripts',
        'func': copy_bdr_scripts,
        'args': (source_dir, user_project_dir),
        'kwargs': {
            'files_to_copy': [
                'deploy_fusion_runner.py',
                'build_and_deploy_venv_locked.bat',
                'requirements.txt',
                'launch_installer.bat'  # ← added to make sure it gets copied
            ],
            'confirm_overwrite': True
        }
    })

    # Step 2: Create isolated virtual environment for internal tool use
    steps.append({
        'name': 'Create Internal BDR Env',
        'func': create_venv,
        'args': (bdr_env_path,),
        'kwargs': {}
    })

    # Step 3: Only install if requirements.txt is present
    steps.append({
        'name': 'Install Requirements',
        'func': install_requirements,
        'args': (bdr_env_path, bdr_requirements_path),
        'kwargs': {}
    })

    # Step 4: Create user CLI environment (for final interaction)
    steps.append({
        'name': 'Create User CLI Venv',
        'func': prepare_and_run_installation,
        'args': (user_project_dir,),
        'kwargs': {}
    })

    return steps

# --- Main Trigger ---
if __name__ == "__main__":
    import os
    import queue
    import threading

    # Stubbed example paths — replace these with real ones as needed
    source_dir = os.path.abspath("./")
    user_project_dir = os.path.abspath("./user_project")
    bdr_env_path = os.path.join(user_project_dir, "venv")
    bdr_requirements_path = os.path.join(source_dir, "requirements.txt")

    steps = build_steps(
        source_dir=source_dir,
        user_project_dir=user_project_dir,
        bdr_env_path=bdr_env_path,
        bdr_requirements_path=bdr_requirements_path
    )

    config = {
        "bdr_source_dir": source_dir,
        "target_project_dir": user_project_dir,
        "installer_steps": steps,
        "final_bat_command": "launch_installer.bat"
    }

    log_to_queue = queue.Queue()
    stop_event = threading.Event()

    run_installation(config, log_to_queue, stop_event)
