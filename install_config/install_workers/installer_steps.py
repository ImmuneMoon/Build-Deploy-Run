# install_config/install_workers/installer_steps.py
import logging, queue, threading, traceback, os, subprocess, time
from pathlib import Path
from typing import List, Optional, Dict, Any

# Make sure these imports are correct based on your project structure
# Assuming manage_user_project_venv will be added to venv_utils.py
from .venv_utils import create_venv, install_requirements, manage_user_project_venv
from .deploy_config import generate_deploy_config # Assuming this function exists
from .install_utils import copy_bdr_scripts, generate_batch_script


logger = logging.getLogger(__name__)

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
    app_instance: Optional[Any] = None
) -> bool:

    """
    Prepares install configuration and runs installation steps defined by build_steps.
    Handles passing necessary configuration down to the steps.
    """
    logger.info(f"Preparing installation for project: {user_project_dir}")
    logger.info(f"  Source Dir: {source_dir}")
    logger.info(f"  Entrypoint: {entrypoint}")
    logger.info(f"  Force Replace User Venv: {force_replace_user_env}")
    logger.info(f"  Skip Docker: {skip_docker}")

    bdr_dest_path = user_project_dir / "Build_Deploy_Run"
    bdr_env_path = bdr_dest_path / ".venv"
    # Define path to BDR's requirements file (must be copied by copy_bdr_scripts)
    bdr_requirements_path = bdr_dest_path / "requirements.txt"

    try:
        # Build the list of steps, passing necessary parameters
        steps = build_steps(
            source_dir=source_dir,
            user_project_dir=user_project_dir,
            bdr_env_path=bdr_env_path,
            bdr_requirements_path=bdr_requirements_path,
            force_replace_user_env=force_replace_user_env,
            entrypoint=entrypoint,
            skip_docker=skip_docker,
            docker_path=docker_path,
            xwindows_path=xwindows_path,
            open_project=open_project
        )

        logger.debug(f"Successfully built {len(steps)} installation steps.")

    except Exception as e:
        logger.error(f"Failed to build installation steps: {e}", exc_info=True)
        if log_queue:
            log_queue.put((logging.CRITICAL, f"Failed to build installation steps: {e}"))
        return False

    # Prepare configuration dictionary for start_installation
    config = {
        "installer_steps": steps,
        "app_instance": app_instance
    }

    try:
        # Ensure log_queue and stop_event are instantiated if None
        effective_log_queue = log_queue if log_queue is not None else queue.Queue()
        effective_stop_event = stop_event if stop_event is not None else threading.Event()
        logger.info("Starting installation sequence execution...")
        success = start_installation(config, effective_log_queue, effective_stop_event)
        if success:
            logger.info("Installation sequence completed successfully.")
        else:
            logger.warning("Installation sequence did not complete successfully or was cancelled.")
        return success
    except Exception as e:
        logger.error(f"Installation failed during start_installation execution: {e}", exc_info=True)
        if log_queue:
            log_queue.put((logging.CRITICAL, f"Installation execution failed: {e}"))
        return False


# --- Step Execution Function ---
def start_installation(config: Dict[str, Any], log_queue: queue.Queue, stop_event: threading.Event) -> bool:
    """
    Runs a list of installer steps sequentially with logging and cancellation support.
    Expects config dictionary with 'installer_steps' key containing a list of step dicts.
    """
    logger.debug("start_installation: Running steps...")
    steps = []
    try:
        # Validate config and steps list
        if not isinstance(config, dict):
            logger.error(f"start_installation: 'config' is not a dict! Type: {type(config)}")
            log_queue.put((logging.CRITICAL, "'config' is not a dictionary."))
            return False

        steps = config.get("installer_steps")
        if steps is None:
            logger.error("start_installation: 'installer_steps' key missing in config.")
            log_queue.put((logging.CRITICAL, "'installer_steps' missing in config."))
            return False
        if not isinstance(steps, list):
            logger.error(f"start_installation: 'installer_steps' is not a list! Type: {type(steps)}")
            log_queue.put((logging.CRITICAL,"'installer_steps' is not a list."))
            return False
        if not steps:
            logger.warning("start_installation: No installer steps found to execute.")
            log_queue.put((logging.WARNING,"No installation steps provided."))
            return True # Success (nothing to do)

        logger.info(f"Starting execution of {len(steps)} installation steps.")

        # Loop through steps
        for i, step in enumerate(steps, start=1):
            if stop_event.is_set():
                logger.warning("Stop event detected. Halting installation.")
                log_queue.put((logging.WARNING,"Installation cancelled by user."))
                return False # Indicate cancellation/failure

            # Validate step structure
            if not isinstance(step, dict):
                logger.error(f"Step {i} definition is not a dictionary. Skipping.")
                log_queue.put((logging.ERROR, f"Step {i} is not correctly defined (not a dict)."))
                continue

            name = step.get("name", f"Unnamed Step {i}")
            func = step.get("func")
            args = step.get("args", [])
            kwargs = step.get("kwargs", {})
            test_func = step.get("test") # Optional post-condition test function

            if not callable(func):
                logger.error(f"Function not defined or not callable for step '{name}'. Skipping.")
                log_queue.put((logging.ERROR, f"No valid function for step '{name}'."))
                continue

            logger.info(f"--- Running Step {i}/{len(steps)}: {name} ---")
            log_queue.put((logging.INFO, f"Starting: {name}"))

            try:
                # Execute the step function
                func(*args, **kwargs)
                logger.info(f"Successfully completed step: {name}")
                log_queue.put((logging.INFO, f"Completed: {name}"))

                # Run post-condition test if provided
                if callable(test_func):
                    logger.debug(f"Running test for step '{name}'...")
                    if not test_func():
                        logger.error(f"Test FAILED for step: {name}. Stopping installation.")
                        log_queue.put((logging.ERROR, f"Test failed after step: {name}"))
                        return False # Stop sequence if test fails
                    else:
                        logger.debug(f"Test PASSED for step '{name}'.")

            except Exception as e:
                error_msg = f"Error during step '{name}': {type(e).__name__}: {e}"
                 # Use traceback import here
                tb_info = traceback.format_exc()
                logger.error(error_msg, exc_info=True) # exc_info=True adds traceback automatically to logger if configured
                # Send simpler message to GUI log queue
                log_queue.put((logging.ERROR, f"FAILED: {name} - {type(e).__name__}"))
                # Send traceback snippet to queue for debugging if needed
                log_queue.put((logging.DEBUG, f"Traceback snippet:\n{tb_info.splitlines()[-1]}"))

                if log_queue:
                    log_queue.put(f"[INSTALL FAILURE] {str(e)}")
                    raise RuntimeError(f"[INSTALL FAILURE] Step '{name}' failed: {e}")
                
                return False # Stop sequence on any exception during a step

            finally:
                if stop_event and stop_event.is_set():
                    logger.warning("[INSTALL] Operation interrupted by user.")
                    

        logger.info("All installation steps completed successfully.")
        return True # All steps completed without error or cancellation

    except Exception as outer_e:
        # Catch errors happening outside the step loop (e.g., config validation)
        tb_info = traceback.format_exc() # Use traceback import here
        logger.critical("Critical error during installation setup.", exc_info=True)
        log_queue.put((logging.CRITICAL, f"Installer setup failed: {outer_e}"))
        log_queue.put((logging.DEBUG, f"Traceback snippet:\n{tb_info.splitlines()[-1]}"))
        return False


# --- Function to run the batch script ---
def run_build_deploy_batch_script(
    bdr_target_dir: Path,
    entrypoint: str,
    skip_docker: bool,
    docker_path: Optional[str] = None, # Add docker_path
    xwindows_path: Optional[str] = None, # Add xwindows_path
    open_project: bool = False, # Add open_project
    log_queue: Optional[queue.Queue] = None,
    stop_event: Optional[threading.Event] = None
):
    """Runs the build_and_deploy_venv_locked.bat script with the specified entrypoint and deployment options."""
    logger.info("Running build and deploy batch script...")

    batch_script_path = bdr_target_dir / "build_and_deploy_venv_locked.bat"

    if not batch_script_path.is_file():
        error_msg = f"Error: Batch script not found at: {batch_script_path}"
        logger.error(error_msg)
        if log_queue:
            log_queue.put((logging.ERROR, error_msg))
        raise FileNotFoundError(error_msg)

    # Construct the command to run the batch script
    command = [
        str(batch_script_path),  # Path to the batch script
        str(Path(bdr_target_dir).parent / entrypoint) # The full path to the entrypoint relative to project root
    ]

    if skip_docker:
        command.append("--skip-docker")

    # Add docker_path, xwindows_path, and open_project as arguments
    # Assuming deploy_fusion_runner.py expects them like this
    if docker_path:
        command.extend(["--docker-path", docker_path])
    if xwindows_path:
        command.extend(["--xwindows-path", xwindows_path])
    if open_project:
        command.append("--open-project") # Assuming --open-project is a flag with no value

    logger.info(f"Executing batch script command: {' '.join(command)}")
    if log_queue:
        log_queue.put((logging.INFO, f"Running: {' '.join(command)}"))

    try:
        process = subprocess.Popen(
            command,
            cwd=str(Path(bdr_target_dir).parent),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            shell=True
        )

        while process.poll() is None:
            if stop_event and stop_event.is_set():
                logger.warning("Stop event set, terminating batch process.")
                process.terminate()
                raise InterruptedError("Installation cancelled by user.")

            stdout_line = process.stdout.readline()
            if stdout_line:
                if log_queue:
                    log_queue.put((logging.INFO, stdout_line.strip()))
            stderr_line = process.stderr.readline()
            if stderr_line:
                if log_queue:
                    log_queue.put((logging.ERROR, stderr_line.strip()))
            time.sleep(0.05)

        stdout_remainder, stderr_remainder = process.communicate()
        if stdout_remainder:
             if log_queue:
                log_queue.put((logging.INFO, stdout_remainder.strip()))
        if stderr_remainder:
             if log_queue:
                log_queue.put((logging.ERROR, stderr_remainder.strip()))

        return_code = process.returncode
        if return_code != 0:
            error_msg = f"Batch script failed with return code: {return_code}"
            logger.error(error_msg)
            if log_queue:
                log_queue.put((logging.ERROR, error_msg))
            raise RuntimeError(error_msg)
        else:
            logger.info("Batch script executed successfully.")

    except FileNotFoundError:
        pass
    except InterruptedError:
        if log_queue:
            log_queue.put((logging.WARNING, "Build and Deploy cancelled."))
        raise
    except Exception as e:
        error_msg = f"Error running batch script: {e}"
        logger.error(error_msg, exc_info=True)
        if log_queue:
            log_queue.put((logging.ERROR, error_msg))
        raise



# --- Build Steps Function ---
def build_steps(
    source_dir: Path,
    user_project_dir: Path,
    bdr_env_path: Path,
    bdr_requirements_path: Path,
    force_replace_user_env: bool, # Flag from GUI
    entrypoint: str,              # Entrypoint from GUI
    skip_docker: bool ,
    docker_path: str,
    xwindows_path: str,
    open_project: bool
) -> List[Dict[str, Any]]:
    """Builds the sequence of installation steps, including managing user venv."""
    logger.debug("Building installation step list...")
    bdr_target_dir = user_project_dir / "Build_Deploy_Run"

    # Determine correct script subfolder based on OS (using os import)
    scripts_subdir = "Scripts" if os.name == 'nt' else "bin"

    # Define paths needed for tests or args using the correct subdir
    bdr_python_exe = bdr_env_path / scripts_subdir / "python.exe" if os.name == 'nt' else bdr_env_path / scripts_subdir / "python"
    user_venv_python_exe = user_project_dir / ".venv" / scripts_subdir / "python.exe" if os.name == 'nt' else user_project_dir / ".venv" / scripts_subdir / "python"


    steps = [
        {
            "name": "Copy BDR Scripts",
            "func": copy_bdr_scripts,
            "args": [source_dir, bdr_target_dir],
            "kwargs": {"confirm_overwrite": True},
            # Test if key files were copied
            "test": lambda: (bdr_target_dir / "deploy_fusion_runner.py").is_file() and \
                            (bdr_target_dir / "requirements.txt").is_file() and \
                            (bdr_target_dir / "workers").is_dir()
        },
        {
            "name": "Create Internal BDR Virtual Environment",
            "func": create_venv,
            "args": [bdr_env_path],
            "kwargs": {"force_delete": True}, # Always create fresh BDR venv
            "test": lambda: bdr_python_exe.is_file() # Check if python exists in venv
        },
        {
            "name": "Install Requirements into BDR Venv",
            "func": install_requirements,
            "args": [bdr_env_path, bdr_requirements_path],
            "kwargs": {"strict": True},
            "test": lambda: bdr_python_exe.is_file() and bdr_requirements_path.is_file()
        },
        {
            # Assumes manage_user_project_venv is added to venv_utils.py
            "name": "Manage User Project Virtual Environment",
            "func": manage_user_project_venv,
            "args": [user_project_dir],
            "kwargs": {"force_delete": force_replace_user_env}, # Use flag from GUI
            "test": lambda: user_venv_python_exe.is_file() # Test if user venv python exists
        },
        {
            "name": "Generate Deployment Batch Script",
            "func": generate_batch_script, # From install_utils.py - make sure this generates the updated batch script
            "args": [bdr_target_dir],
            "kwargs": {},
            "test": lambda: (bdr_target_dir / "build_and_deploy_venv_locked.bat").exists()
        },
        {
            "name": "Run Build and Deploy Batch Script",
            "func": run_build_deploy_batch_script, # New function to add
            "args": [bdr_target_dir, entrypoint, skip_docker], # Pass BDR dir, entrypoint, and skip_docker flag
            "kwargs": {
                "docker_path": docker_path,  # Pass docker_path
                "xwindows_path": xwindows_path, # Pass xwindows_path
                "open_project": open_project   # Pass open_project
            },
            "test": lambda: True # Or add a test if possible (e.g., check for build artifacts)
        }
    ]
    logger.debug(f"Built {len(steps)} steps.")
    return steps
