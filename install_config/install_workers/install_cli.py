# install_config/install_workers/install_cli.py

import argparse, sys, logging, queue
from pathlib import Path
from install_config.install_workers.installer_steps import prepare_and_run_installation
from install_config.install_workers.install_core import generate_deploy_config
from install_config.install_workers.GUI.gui_utils import log_to_queue

def main():
    parser = argparse.ArgumentParser(
        description="Run Build-Deploy-Run installer from CLI"
    )
    parser.add_argument('--xwindows', required=True, help="Path to xwindows folder")
    parser.add_argument('--docker', required=True, help="Path to Docker folder")
    parser.add_argument('--project', required=True, help="Path to user's project root")
    parser.add_argument('--entrypoint', default='main.py', help="Main Python entrypoint file")
    parser.add_argument('--skip-docker', action='store_true', help="Skip Docker deployment step")
    parser.add_argument('--open', action='store_true', help="Open selected paths post-install")
    parser.add_argument('--auto-confirm', action='store_true', help="Auto confirm prompts (e.g., env deletion)")
    parser.add_argument('--verbose', action='store_true', help="Enable verbose logging")

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format='[%(levelname)s] %(message)s'
    )

    logging.info("🚀 Starting CLI installation...")

    # Define log queue for compatibility with shared logic
    log_q = queue.Queue()

    # Set the BDR source directory to the current script's parent
    source_dir = Path(__file__).resolve().parent

    # Generate deploy_config.json
    generate_deploy_config(
        target_project_dir=Path(args.project),
        entrypoint=args.entrypoint,
        docker_path=args.docker,
        xwindows_path=args.xwindows,
        open_project=args.open
    )

    # Run installer
    success = prepare_and_run_installation(
        source_dir=source_dir,
        user_project_dir=Path(args.project),
        entrypoint=args.entrypoint,
        docker_required=not args.skip_docker,
        auto_confirm=args.auto_confirm,
        log_q=log_q
    )

    if success:
        log_to_queue(log_q, "✅ Installation complete!", logging.INFO)
        print("\n[✔] You may now run the generated CLI script:")
        print("    .\\Build_Deploy_Run\\build_and_deploy_venv_locked.bat")
        sys.exit(0)
    else:
        log_to_queue(log_q, "❌ Installation failed. Check logs for details.", logging.ERROR)
        sys.exit(1)

if __name__ == "__main__":
    main()
