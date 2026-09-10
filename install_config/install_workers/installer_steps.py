# install_config/install_workers/installer_steps.py
import logging
import os
import queue
import subprocess
import threading
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional

from .venv_utils import create_venv, install_requirements, manage_user_project_venv
from .deploy_config import generate_deploy_config
from .install_utils import copy_bdr_scripts, generate_batch_script, BATCH_SCRIPT_NAME

logger = logging.getLogger(__name__)

BDR_FOLDER_NAME = "Build_Deploy_Run"
# The GUI exe is windowed; without this flag every child process would flash a console window.
NO_WINDOW = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0


# --- Main Orchestration Function ---
def prepare_and_run_installation(
    source_dir: Path,
    user_project_dir: Path,
    entrypoint: str,
    force_replace_user_env: bool,
    open_project: bool,
    docker_path: Optional[str] = None,
    xwindows_path: Optional[str] = None,
    log_queue: Optional[queue.Queue] = None,
    stop_event: Optional[threading.Event] = None,
    skip_docker: bool = False,
    skip_exe: bool = False,
    run_after_install: bool = True,
    app_instance: Optional[Any] = None,
) -> bool:
    """Builds the installation step list and runs it. Returns True only if every step succeeded."""
    source_dir = Path(source_dir)
    user_project_dir = Path(user_project_dir)
    logger.info(f"Preparing installation for project: {user_project_dir}")
    logger.info(f"  Source Dir: {source_dir}")
    logger.info(f"  Entrypoint: {entrypoint}")
    logger.info(f"  Force Replace User Venv: {force_replace_user_env}")
    logger.info(f"  Skip Docker: {skip_docker}")
    logger.info(f"  Skip EXE: {skip_exe}")
    logger.info(f"  Run build after install: {run_after_install}")

    bdr_dest_path = user_project_dir / BDR_FOLDER_NAME
    bdr_env_path = bdr_dest_path / ".venv"
    bdr_requirements_path = bdr_dest_path / "requirements.txt"

    effective_log_queue = log_queue if log_queue is not None else queue.Queue()
    effective_stop_event = stop_event if stop_event is not None else threading.Event()

    try:
        steps = build_steps(
            source_dir=source_dir,
            user_project_dir=user_project_dir,
            bdr_env_path=bdr_env_path,
            bdr_requirements_path=bdr_requirements_path,
            force_replace_user_env=force_replace_user_env,
            entrypoint=entrypoint,
            skip_docker=skip_docker,
            skip_exe=skip_exe,
            docker_path=docker_path,
            xwindows_path=xwindows_path,
            open_project=open_project,
            run_after_install=run_after_install,
            log_queue=effective_log_queue,
            stop_event=effective_stop_event,
        )
    except Exception as e:
        logger.error(f"Failed to build installation steps: {e}", exc_info=True)
        effective_log_queue.put((logging.CRITICAL, f"Failed to build installation steps: {e}"))
        return False

    try:
        logger.info("Starting installation sequence execution...")
        success = start_installation({"installer_steps": steps}, effective_log_queue, effective_stop_event)
        if success:
            logger.info("Installation sequence completed successfully.")
        else:
            logger.warning("Installation sequence did not complete successfully or was cancelled.")
        return success
    except Exception as e:
        logger.error(f"Installation failed during start_installation execution: {e}", exc_info=True)
        effective_log_queue.put((logging.CRITICAL, f"Installation execution failed: {e}"))
        return False


# --- Step Execution Function ---
def start_installation(config: Dict[str, Any], log_queue: queue.Queue, stop_event: threading.Event) -> bool:
    """Runs installer steps sequentially with logging and cancellation support."""
    steps = config.get("installer_steps") if isinstance(config, dict) else None
    if not isinstance(steps, list):
        logger.error("start_installation: 'installer_steps' missing or not a list.")
        log_queue.put((logging.CRITICAL, "'installer_steps' missing or not a list."))
        return False
    if not steps:
        log_queue.put((logging.WARNING, "No installation steps provided."))
        return True

    logger.info(f"Starting execution of {len(steps)} installation steps.")
    for i, step in enumerate(steps, start=1):
        if stop_event.is_set():
            logger.warning("Stop event detected. Halting installation.")
            log_queue.put((logging.WARNING, "Build cancelled by user."))
            return False

        name = step.get("name", f"Unnamed Step {i}")
        func = step.get("func")
        args = step.get("args", [])
        kwargs = step.get("kwargs", {})
        test_func = step.get("test")

        if not callable(func):
            logger.error(f"No valid function for step '{name}'.")
            log_queue.put((logging.ERROR, f"No valid function for step '{name}'."))
            return False

        logger.info(f"--- Running Step {i}/{len(steps)}: {name} ---")
        log_queue.put((logging.INFO, f"[{i}/{len(steps)}] Starting: {name}"))
        try:
            func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error during step '{name}': {type(e).__name__}: {e}", exc_info=True)
            log_queue.put((logging.ERROR, f"FAILED: {name} - {type(e).__name__}: {e}"))
            log_queue.put((logging.DEBUG, traceback.format_exc().strip().splitlines()[-1]))
            return False

        if callable(test_func) and not test_func():
            logger.error(f"Post-condition check FAILED for step: {name}.")
            log_queue.put((logging.ERROR, f"Check failed after step: {name}"))
            return False

        logger.info(f"Completed step: {name}")
        log_queue.put((logging.INFO, f"Completed: {name}"))

    logger.info("All installation steps completed successfully.")
    return True


# --- Helpers used as steps ---
def write_deploy_config_step(bdr_target_dir: Path, **kwargs):
    if not generate_deploy_config(bdr_target_dir, **kwargs):
        raise RuntimeError("Could not write .deploy_config")


def open_project_folder(project_dir: Path):
    project_dir = Path(project_dir)
    try:
        if os.name == "nt":
            os.startfile(str(project_dir))  # type: ignore[attr-defined]
        else:
            subprocess.Popen(["xdg-open", str(project_dir)])
        logger.info(f"Opened project folder: {project_dir}")
    except Exception as e:
        # Not worth failing the install over.
        logger.warning(f"Could not open project folder {project_dir}: {e}")


def run_build_deploy_batch_script(
    bdr_target_dir: Path,
    entrypoint: str,
    skip_docker: bool,
    skip_exe: bool = False,
    log_queue: Optional[queue.Queue] = None,
    stop_event: Optional[threading.Event] = None,
):
    """Runs the generated batch script (non-interactively) and streams its output to the log queue."""
    bdr_target_dir = Path(bdr_target_dir)
    project_dir = bdr_target_dir.parent
    batch_script_path = bdr_target_dir / BATCH_SCRIPT_NAME
    if not batch_script_path.is_file():
        raise FileNotFoundError(f"Batch script not found at: {batch_script_path}")

    command = ["cmd.exe", "/c", str(batch_script_path), entrypoint, "--no-pause"]
    if skip_docker:
        command.append("--skip-docker")
    if skip_exe:
        command.append("--skip-exe")

    env = os.environ.copy()
    env["BDR_NO_PAUSE"] = "1"

    logger.info(f"Executing batch script: {' '.join(command)}")
    if log_queue:
        log_queue.put((logging.INFO, f"Running: {' '.join(command)}"))

    process = subprocess.Popen(
        command,
        cwd=str(project_dir),
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
        creationflags=NO_WINDOW,
    )
    try:
        for line in iter(process.stdout.readline, ""):
            line = line.rstrip()
            if line and log_queue:
                level = logging.ERROR if ("[ERROR]" in line or "ERROR -" in line) else logging.INFO
                log_queue.put((level, line))
            if stop_event and stop_event.is_set():
                process.terminate()
                raise InterruptedError("Build cancelled by user.")
    finally:
        process.stdout.close()
        return_code = process.wait()

    if return_code != 0:
        raise RuntimeError(f"Batch script failed with return code {return_code}. See the log above.")
    logger.info("Batch script executed successfully.")


# --- Build Steps Function ---
def build_steps(
    source_dir: Path,
    user_project_dir: Path,
    bdr_env_path: Path,
    bdr_requirements_path: Path,
    force_replace_user_env: bool,
    entrypoint: str,
    skip_docker: bool,
    skip_exe: bool,
    docker_path: Optional[str],
    xwindows_path: Optional[str],
    open_project: bool,
    run_after_install: bool,
    log_queue: Optional[queue.Queue] = None,
    stop_event: Optional[threading.Event] = None,
) -> List[Dict[str, Any]]:
    """Builds the sequence of installation steps."""
    bdr_target_dir = user_project_dir / BDR_FOLDER_NAME
    scripts_subdir = "Scripts" if os.name == "nt" else "bin"
    python_name = "python.exe" if os.name == "nt" else "python"
    bdr_python_exe = bdr_env_path / scripts_subdir / python_name
    user_venv_python_exe = user_project_dir / ".venv" / scripts_subdir / python_name
    expected_exe = user_project_dir / "dist" / (Path(entrypoint).stem + (".exe" if os.name == "nt" else ""))

    steps: List[Dict[str, Any]] = [
        {
            "name": "Copy build tools into project",
            "func": copy_bdr_scripts,
            "args": [source_dir, bdr_target_dir],
            "kwargs": {"confirm_overwrite": True},
            "test": lambda: (bdr_target_dir / "deploy_fusion_runner.py").is_file()
                            and (bdr_target_dir / "requirements.txt").is_file()
                            and (bdr_target_dir / "workers").is_dir(),
        },
        {
            "name": "Create build-tools venv",
            "func": create_venv,
            "args": [bdr_env_path],
            "kwargs": {"force_delete": True},
            "test": lambda: bdr_python_exe.is_file(),
        },
        {
            "name": "Install PyInstaller into build-tools venv",
            "func": install_requirements,
            "args": [bdr_env_path, bdr_requirements_path],
            "kwargs": {"strict": True},
            "test": lambda: bdr_python_exe.is_file(),
        },
        {
            "name": "Set up project venv",
            "func": manage_user_project_venv,
            "args": [user_project_dir],
            "kwargs": {"force_delete": force_replace_user_env},
            "test": lambda: user_venv_python_exe.is_file(),
        },
        {
            "name": "Save build settings",
            "func": write_deploy_config_step,
            "args": [bdr_target_dir],
            "kwargs": {
                "entrypoint": entrypoint,
                "skip_docker": skip_docker,
                "skip_exe": skip_exe,
                "docker_path": docker_path or "",
                "xwindows_path": xwindows_path or "",
                "open_project": open_project,
            },
            "test": lambda: (bdr_target_dir / ".deploy_config").is_file(),
        },
        {
            "name": "Generate build script",
            "func": generate_batch_script,
            "args": [bdr_target_dir],
            "kwargs": {},
            "test": lambda: (bdr_target_dir / BATCH_SCRIPT_NAME).is_file(),
        },
    ]

    if run_after_install:
        steps.append({
            "name": "Package project (EXE / Docker)",
            "func": run_build_deploy_batch_script,
            "args": [bdr_target_dir, entrypoint, skip_docker],
            "kwargs": {"skip_exe": skip_exe, "log_queue": log_queue, "stop_event": stop_event},
            # The runner verifies the Docker image itself; here we only re-check the EXE on disk.
            "test": (lambda: True) if skip_exe else (lambda: expected_exe.is_file()),
        })

    if open_project:
        steps.append({
            "name": "Open Project Folder",
            "func": open_project_folder,
            "args": [user_project_dir],
            "kwargs": {},
        })

    logger.debug(f"Built {len(steps)} steps.")
    return steps
