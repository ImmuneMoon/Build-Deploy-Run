# install_config/ install_workers/ venv_utils.py

import logging, subprocess, shutil, os, json
from pathlib import Path

logger = logging.getLogger(__name__)


def write_bdr_config_file(target_dir, xwindows_path=None, docker_path=None, open_paths=None):
    """
    Write deployment configuration metadata into Build_Deploy_Run/deploy_config.json
    
    :param target_dir: Path to the project root (should contain Build_Deploy_Run)
    :param xwindows_path: Optional X server executable path
    :param docker_path: Optional Docker executable path
    :param open_paths: List of additional openable paths (optional)
    """
    logger = logging.getLogger(__name__)

    try:
        # Make sure target_dir is Path object
        target_dir = Path(target_dir)
        bdr_dir = target_dir / 'Build_Deploy_Run'
        bdr_dir.mkdir(parents=True, exist_ok=True)

        config_data = {
            "docker_path": docker_path or "",
            "xwindows_path": xwindows_path or "",
            "open_paths": open_paths or []
        }

        config_path = bdr_dir / 'deploy_config.json'

        with config_path.open('w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=4)

        logger.info(f"Deploy config written to: {config_path}")

    except Exception as e:
        logger.error(f"Failed to write deploy config: {e}", exc_info=True)
        raise


# --- Centralized Venv Script Directory Resolver ---
def get_venv_scripts_dir(venv_path: Path) -> Path:
    return venv_path / ("Scripts" if os.name == "nt" else "bin")


# --- System Python Finder ---
def find_system_python() -> Path:
    python_exe = shutil.which("python")
    if not python_exe:
        raise RuntimeError("System Python executable not found in PATH.")
    return Path(python_exe)


# --- Venv Creator ---
def create_venv(path: Path, force_delete: bool = False):
    path = Path(path)

    if path.exists():
        if force_delete:
            logger.warning(f"[VENV] Removing existing venv at: {path}")
            shutil.rmtree(path)
        else:
            venv_python = get_venv_scripts_dir(path) / ("python.exe" if os.name == "nt" else "python")
            if venv_python.is_file():
                logger.info(f"[VENV] Existing venv seems valid: {path}")
                return
            else:
                raise RuntimeError(f"Invalid venv at {path}, and force_delete=False.")

    logger.info(f"[VENV] Creating virtual environment at {path}...")
    system_python = find_system_python()

    try:
        subprocess.run([str(system_python), "-m", "venv", str(path)], check=True, capture_output=True, text=True)
        logger.info(f"[VENV] Created successfully at {path}")

        # Post-creation sanity check
        venv_python = get_venv_scripts_dir(path) / ("python.exe" if os.name == "nt" else "python")
        if not venv_python.is_file():
            raise RuntimeError(f"Python binary missing after venv creation at {path}")

        subprocess.run([str(venv_python), "--version"], check=True, capture_output=True, timeout=10)
    except Exception as e:
        logger.critical(f"[VENV ERROR] Venv creation failed: {e}")
        if path.exists():
            shutil.rmtree(path)
        raise


# --- Requirements Installer ---
def install_requirements(venv_path: Path, requirements_file: Path, strict: bool = False):
    venv_path = Path(venv_path)
    requirements_file = Path(requirements_file)

    venv_python = get_venv_scripts_dir(venv_path) / ("python.exe" if os.name == "nt" else "python")
    pip_exe = get_venv_scripts_dir(venv_path) / ("pip.exe" if os.name == "nt" else "pip")

    if not venv_python.is_file() or not pip_exe.is_file():
        raise RuntimeError("Python or pip missing from venv. Cannot install requirements.")

    if not requirements_file.is_file():
        msg = f"Requirements file not found: {requirements_file}"
        if strict:
            raise FileNotFoundError(msg)
        else:
            logger.warning(msg)
            return

    env = os.environ.copy()
    env.pop('PYTHONHOME', None)
    env.pop('PYTHONPATH', None)
    env['PATH'] = f"{get_venv_scripts_dir(venv_path)}{os.pathsep}{env.get('PATH', '')}"

    try:
        subprocess.run([str(venv_python), "-m", "pip", "install", "--upgrade", "pip"],
                       check=False, capture_output=True, text=True, env=env)

        subprocess.run([str(venv_python), "-m", "pip", "install", "-r", str(requirements_file)],
                       check=True, capture_output=True, text=True, env=env)

        logger.info("[PIP INSTALL] Requirements installed successfully.")
    except subprocess.CalledProcessError as e:
        logger.error(f"[PIP INSTALL ERROR] {e}")
        if venv_path.exists():
            shutil.rmtree(venv_path)
        raise


# --- Venv Manager ---
def manage_user_project_venv(user_project_dir: Path, force_delete: bool = False):
    venv_dir = Path(user_project_dir) / ".venv"

    if venv_dir.exists():
        if force_delete:
            shutil.rmtree(venv_dir)
            logger.info(f"[USER VENV] Removed existing venv at {venv_dir}")
        else:
            return

    create_venv(venv_dir, force_delete=False)
    logger.info(f"[USER VENV] Ready at {venv_dir}")
