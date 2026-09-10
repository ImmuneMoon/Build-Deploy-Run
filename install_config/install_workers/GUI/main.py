# install_config/install_workers/GUI/main.py
"""
Entry point for Build Deploy Run.

  No arguments      -> opens the Tkinter GUI.
  --project <dir>   -> headless mode: runs the same installation steps without a window
                       (useful for scripting and for testing the frozen EXE).
"""

import argparse
import logging
import os
import queue
import sys
import threading
from pathlib import Path



def _attach_parent_console():
    """
    The exe is built windowed (no console). When it is launched from a terminal in headless mode,
    attach to that terminal so print()/logging output is visible. If stdout is already redirected
    (a pipe or file), Python has a usable stream and nothing needs to change.
    """
    if os.name != "nt" or sys.stdout is not None:
        return
    try:
        import ctypes
        if ctypes.windll.kernel32.AttachConsole(-1):  # ATTACH_PARENT_PROCESS
            sys.stdout = open("CONOUT$", "w", encoding="utf-8", errors="replace", buffering=1)
            sys.stderr = sys.stdout
    except Exception:
        pass


def _configure_logging():
    if sys.stderr is not None:
        logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(name)s: %(message)s")
    else:
        logging.getLogger().addHandler(logging.NullHandler())


DEFAULT_CONFIG = {
    "BDR_FOLDER_NAME": "Build_Deploy_Run",
    "PROJECT_ROOT": str(Path.cwd()),
    "FINAL_BAT_COMMAND": r".\Build_Deploy_Run\build_and_deploy_venv_locked.bat",
}


def launch_gui(config_constants):
    import tkinter as tk
    from install_config.install_workers.GUI.main_view import InstallerApp

    log_q = queue.Queue()
    root = tk.Tk()
    InstallerApp(root, config_constants, log_q)
    root.mainloop()


def run_headless(args) -> int:
    from install_config.install_workers import installer_steps
    from install_config.install_workers.install_utils import get_bdr_source_dir

    project_dir = Path(args.project).resolve()
    if not project_dir.is_dir():
        print(f"[ERROR] Project directory does not exist: {project_dir}")
        return 2
    if not (project_dir / args.entrypoint).is_file():
        print(f"[ERROR] Entrypoint not found inside the project: {project_dir / args.entrypoint}")
        return 2

    log_q: queue.Queue = queue.Queue()
    stop_event = threading.Event()

    def drain():
        while True:
            item = log_q.get()
            if item is None:
                return
            level, msg = item if isinstance(item, tuple) and len(item) == 2 else (logging.INFO, str(item))
            print(f"[{logging.getLevelName(level)}] {msg}", flush=True)

    printer = threading.Thread(target=drain, daemon=True)
    printer.start()

    success = installer_steps.prepare_and_run_installation(
        source_dir=get_bdr_source_dir(),
        user_project_dir=project_dir,
        entrypoint=args.entrypoint,
        force_replace_user_env=args.replace_venv,
        open_project=args.open_project,
        docker_path=args.docker_path,
        xwindows_path=args.xwindows_path,
        log_queue=log_q,
        stop_event=stop_event,
        skip_docker=args.skip_docker,
        skip_exe=args.skip_exe,
        run_after_install=not args.no_run,
    )
    log_q.put(None)
    printer.join(timeout=5)

    if success:
        print("\n[OK] Build complete. Rebuild any time with:")
        print(f"    cd \"{project_dir}\" && {DEFAULT_CONFIG['FINAL_BAT_COMMAND']}")
        return 0
    print("\n[FAILED] Build did not complete. See the messages above.")
    return 1


def parse_args(argv):
    parser = argparse.ArgumentParser(description="Build Deploy Run: package a Python project as an EXE and/or Docker image (GUI by default; --project for headless).")
    parser.add_argument("--project", help="Target project directory (enables headless mode)")
    parser.add_argument("--entrypoint", default="main.py", help="Entrypoint script relative to the project root")
    parser.add_argument("--skip-docker", action="store_true", help="Skip the Docker image build (EXE only)")
    parser.add_argument("--skip-exe", action="store_true", help="Skip the EXE build (Docker only)")
    parser.add_argument("--no-run", action="store_true", help="Set up the build tools only; do not package afterwards")
    parser.add_argument("--replace-venv", action="store_true", help="Replace an existing project .venv")
    parser.add_argument("--open-project", action="store_true", help="Open the project folder when finished")
    parser.add_argument("--docker-path", default=None, help="Path to docker executable")
    parser.add_argument("--xwindows-path", default=None, help="Path to vcxsrv.exe")
    args = parser.parse_args(argv)
    if args.skip_docker and args.skip_exe:
        parser.error("--skip-docker and --skip-exe together leave nothing to build.")
    return args


def main(argv=None):
    if "--project" in (sys.argv[1:] if argv is None else argv):
        _attach_parent_console()
    _configure_logging()
    args = parse_args(sys.argv[1:] if argv is None else argv)
    if args.project:
        sys.exit(run_headless(args))
    launch_gui(DEFAULT_CONFIG)


if __name__ == "__main__":
    main()
