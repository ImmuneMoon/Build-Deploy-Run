# workers/freeze.py

import subprocess, logging, queue, sys, shutil, locale
from pathlib import Path

logger = logging.getLogger(__name__)

# --- Log Helper (Optional - needed if using log_q) ---
def _log(log_q, message, level=logging.INFO):
    """Internal helper to log directly and optionally queue."""
    logger.log(level, message)
    if log_q and isinstance(log_q, queue.Queue):
        try:
            log_q.put_nowait(f"[{logging.getLevelName(level)}] {message}")
        except queue.Full: logger.warning("GUI log queue full.")
        except Exception as e: logger.error(f"Error putting message in queue: {e}")

# --- Existing freeze_requirements function (keep as is) ---
def freeze_requirements(output_file="requirements.txt", exclude_editable=True):
    # ... (existing code) ...
    logger.info(f"Freezing requirements to {output_file}, exclude_editable={exclude_editable}")
    try:
        command = [sys.executable, "-m", "pip", "freeze"] # Use current python
        if exclude_editable: command.append("--exclude-editable")
        # Use default encoding of the *current* script's environment here
        result = subprocess.run(command, capture_output=True, text=True, check=True, encoding=locale.getpreferredencoding(False))
        Path(output_file).write_text(result.stdout, encoding='utf-8') # Write as UTF-8
        logger.info(f"Requirements frozen to {output_file}")
        return True
    except subprocess.CalledProcessError as e: logger.error(f"Error freezing requirements: {e}"); return False
    except Exception as e: logger.error(f"Unexpected error freezing requirements: {e}"); return False


# --- Updated generate_filtered_requirements function ---
def find_python_executable(log_q):
    """Tries to find a suitable python.exe/python in PATH."""
    _log(log_q, "Searching for python executable in PATH...", level=logging.DEBUG)
    python_exe = shutil.which("python")
    if python_exe: _log(log_q, f"Found python executable in PATH: {python_exe}", level=logging.INFO); return python_exe
    else: _log(log_q, "Python executable not found in system PATH.", level=logging.ERROR); return None

def generate_filtered_requirements(log_q, project_dir, output_path, bdr_folder_name, venv_folder="venv"):
    """
    Generates requirements.txt using a found system python.exe 'pip freeze'.
    Filters out build dependencies and ignored folders. Logs via queue if provided.
    Handles potential encoding issues from pip freeze.
    """
    _log(log_q, f"Generating clean requirements for {project_dir} using system Python...", level=logging.INFO)

    python_exe = find_python_executable(log_q)
    if not python_exe: _log(log_q, "Cannot generate reqs without python executable.", level=logging.ERROR); return False

    try:
        cmd = [python_exe, "-m", "pip", "freeze", "--exclude-editable"]
        _log(log_q, f"Running: {' '.join(cmd)} in {project_dir}", level=logging.DEBUG)

        # Run and capture raw bytes first
        result = subprocess.run(cmd, capture_output=True, check=True, cwd=project_dir)

        # Detect encoding or use fallback
        output_bytes = result.stdout
        detected_encoding = None
        try:
            # Try UTF-8 first (common)
            output_text = output_bytes.decode('utf-8')
            detected_encoding = 'utf-8'
            _log(log_q, "Decoded pip freeze output as UTF-8.", level=logging.DEBUG)
        except UnicodeDecodeError:
            # If UTF-8 fails, try system's preferred encoding
            preferred_encoding = locale.getpreferredencoding(False)
            _log(log_q, f"UTF-8 decoding failed, trying system preferred: {preferred_encoding}", level=logging.WARNING)
            try:
                output_text = output_bytes.decode(preferred_encoding)
                detected_encoding = preferred_encoding
            except (UnicodeDecodeError, LookupError) as e:
                # If preferred also fails, force replace errors with a common fallback like latin-1
                _log(log_q, f"System preferred encoding '{preferred_encoding}' failed ({e}), falling back to latin-1 with replacements.", level=logging.ERROR)
                output_text = output_bytes.decode('latin-1', errors='replace')
                detected_encoding = 'latin-1 (fallback)'

        lines = output_text.splitlines()
        filtered_lines = []
        ignore_markers = [f"{bdr_folder_name.lower()}", f"{venv_folder.lower()}"]
        build_deps = ["pyinstaller", "pyperclip", "colorama", "pillow"] # Added Pillow
        _log(log_q, f"Filtering pip freeze (ignoring: {ignore_markers}, build deps: {build_deps})...", level=logging.DEBUG)
        for line in lines:
            line_lower = line.lower()
            package_name = ""
            try: package_name = line.split('==')[0].split('<')[0].split('>')[0].split('[')[0].strip().lower()
            except: continue # Skip malformed lines
            is_ignored = any(marker in line_lower for marker in ignore_markers)
            is_build_dep = package_name in build_deps
            if package_name and not is_ignored and not is_build_dep:
                filtered_lines.append(line)
            else:
                _log(log_q, f"Filtering out: {line} (Ignored: {is_ignored}, BuildDep: {is_build_dep})", level=logging.DEBUG)

        if not filtered_lines: _log(log_q, "Warning: No project requirements found after filtering.", level=logging.WARNING)

        # Write the file explicitly as UTF-8
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding='utf-8') as f:
            f.write("\n".join(filtered_lines))

        _log(log_q, f"Clean requirements written: {output_path} ({len(filtered_lines)} pkgs, decoded as {detected_encoding})", level=logging.INFO)
        return True

    except subprocess.CalledProcessError as e:
        # Try decoding stderr as well for error messages
        stderr_text = e.stderr.decode(locale.getpreferredencoding(False), errors='replace') if e.stderr else "(no stderr)"
        stdout_text = e.stdout.decode(locale.getpreferredencoding(False), errors='replace') if e.stdout else "(no stdout)"
        _log(log_q, f"Error running system pip freeze: {stderr_text or stdout_text}", level=logging.ERROR)
        return False
    except Exception as e:
        _log(log_q, f"Error generating requirements file: {e}", level=logging.ERROR)
        import traceback
        _log(log_q, traceback.format_exc(), level=logging.DEBUG)
        return False

# Example usage (keep as is or update if needed)
if __name__ == "__main__":
    # ... (existing test code) ...
    pass