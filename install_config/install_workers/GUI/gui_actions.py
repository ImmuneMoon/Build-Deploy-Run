from pathlib import Path
import shutil
import logging
import subprocess
import traceback
from typing import Union, List, Optional

logger = logging.getLogger(__name__)


def run_command(cmd: Union[str, List[str]], env: Optional[dict] = None, cwd: Optional[Union[str, Path]] = None) -> None:
    """
    Executes a command using subprocess.run with optional environment variables and working directory.
    """
    if not cmd:
        raise ValueError("Command is empty or None.")
    if isinstance(cmd, str):
        cmd = [cmd]
    elif not isinstance(cmd, (list, tuple)):
        raise TypeError("Command must be a string or list of strings.")
    for i, part in enumerate(cmd):
        if not isinstance(part, str):
            raise TypeError(f"Command part at index {i} is not a string: {repr(part)}")

    logger.info(f"[CMD] Running: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True, env=env, cwd=cwd)
        if result.stdout:
            logger.info(result.stdout.strip())
        if result.stderr:
            logger.warning(result.stderr.strip())
    except subprocess.CalledProcessError as e:
        logger.error(f"[ERROR] Command failed: {e}")
        logger.error(f"[STDOUT]\n{e.stdout}")
        logger.error(f"[STDERR]\n{e.stderr}")
        raise
    except Exception as e:
        logger.error(f"[FATAL] Unexpected error: {e}")
        logger.error(traceback.format_exc())
        raise


def copy_entire_bdr_folder(source_dir: Path, target_dir: Path, confirm_overwrite: bool = True) -> Path:
    """
    Copies the entire Build_Deploy_Run folder from source to target.

    Args:
        source_dir (Path): Directory containing the Build_Deploy_Run folder.
        target_dir (Path): Destination directory.
        confirm_overwrite (bool): If True, overwrites the existing directory if it exists.

    Returns:
        Path: Path to the copied Build_Deploy_Run directory.

    Raises:
        FileNotFoundError: If the source folder doesn't exist.
    """
    src_folder = source_dir / "Build_Deploy_Run"
    if not src_folder.exists() or not src_folder.is_dir():
        raise FileNotFoundError(f"[BDR] Expected BDR folder missing: {src_folder}")

    if target_dir.exists():
        if confirm_overwrite:
            logger.warning(f"[BDR] Overwriting existing directory: {target_dir}")
            shutil.rmtree(target_dir)
        else:
            logger.info(f"[BDR] Skipping copy (folder exists, overwrite not confirmed): {target_dir}")
            return target_dir

    shutil.copytree(src_folder, target_dir)
    logger.info(f"[BDR] Folder copied to: {target_dir}")
    return target_dir


def copy_bdr_scripts(source_dir: Union[str, Path], target_project_dir: Union[str, Path], files_to_copy: Optional[List[str]] = None, confirm_overwrite: bool = True) -> Path:
    """
    Copies the Build_Deploy_Run assets to a project's target directory.

    Args:
        source_dir (str or Path): Source directory containing the Build_Deploy_Run folder or specific files.
        target_project_dir (str or Path): Project directory to receive copied files.
        files_to_copy (List[str], optional): Specific files to copy. If None, copies entire Build_Deploy_Run folder.
        confirm_overwrite (bool): If True, allows overwriting existing BDR directory. Defaults to True.

    Returns:
        Path: Path to the destination Build_Deploy_Run directory.

    Raises:
        FileNotFoundError: If expected source files or folders are missing.
    """
    source_dir = Path(source_dir)
    target_dir = Path(target_project_dir) / "Build_Deploy_Run"

    if files_to_copy is None:
        return copy_entire_bdr_folder(source_dir, target_dir, confirm_overwrite)

    target_dir.mkdir(parents=True, exist_ok=True)
    for file_name in files_to_copy:
        src_path = source_dir / file_name
        dst_path = target_dir / file_name
        if not src_path.exists() or not src_path.is_file():
            if file_name == 'requirements.txt':
                logger.warning(f"[BDR] Optional file missing, skipping copy: {src_path}")
                continue
            else:
                raise FileNotFoundError(f"[BDR] Required file missing: {src_path}")

        shutil.copy2(src_path, dst_path)
        logger.info(f"[BDR] Copied {file_name} → {dst_path}")

    return target_dir


def run_step_sequence(steps: List[dict], auto_confirm: bool = False) -> bool:
    """
    Runs a sequence of steps defined by a list of dictionaries.

    Each step should have:
        - name (str)
        - func (callable)
        - args (list, optional)
        - kwargs (dict, optional)
        - test (callable, optional): A post-condition check.

    Returns:
        bool: True if all steps pass; False otherwise.
    """
    for step in steps:
        name = step.get("name", "Unnamed Step")
        func = step.get("func")
        args = step.get("args", [])
        kwargs = step.get("kwargs", {})
        test_fn = step.get("test")

        logger.info(f"▶ Running: {name}")
        try:
            func(*args, **kwargs)
            logger.info(f"✅ Completed: {name}")
            if test_fn and not test_fn():
                logger.warning(f"[WARN] Step '{name}' did not pass its test condition.")
                if not auto_confirm:
                    return False
        except Exception as e:
            logger.error(f"❌ Failed: {name} — {type(e).__name__}: {e}")
            return False

    return True


def notify_command_ready(app):
    """Notifies the user that the deployment command is ready after installation."""
    root_ref = getattr(app, 'root', None)
    messagebox_ref = getattr(app, 'messagebox', None)

    if not all([root_ref, messagebox_ref]):
        if hasattr(app, 'log_message_action'): app.log_message_action("Missing root or messagebox for final command notification.", logging.WARNING)
        return

    messagebox_ref.showinfo(
        "Deployment Command Ready",
        "✅ The deployment command has been copied to your clipboard.\n\nYou can now paste and run it.",
        parent=root_ref
    )
