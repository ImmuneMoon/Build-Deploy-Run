# ./deploy_fusion_runner.py

import argparse, sys
from pathlib import Path
from workers.run_command import run_command
from workers.logger_setup import setup_logger

logger = setup_logger("bdr_installer", "logs/bdr_installer.log")


# --- Constants ---
# CORRECTED: Go up 1 level from the script location (Build_Deploy_Run) to get the project root
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DIST_DIR = PROJECT_ROOT / "dist" # dist dir inside the project root
# Define Dockerfile path relative to the *correct* project root
DOCKERFILE = PROJECT_ROOT / "Dockerfile"
# DEFAULT_ENTRYPOINT = None # No longer needed here as it comes from args/env


# --- EXE Builder ---
def build_exe(entrypoint_full_path: Path):
    """Builds a single-file executable using PyInstaller."""
    if not entrypoint_full_path.is_file(): # Check is_file() specifically
        logger.error(f"[ERROR] Entrypoint is not a valid file: {entrypoint_full_path}")
        sys.exit(1)

    logger.info(f"[BUILD] Building EXE from: {entrypoint_full_path}")
    # Ensure DIST_DIR exists
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    run_command([
        sys.executable, "-m", "PyInstaller",
        "--noconfirm", # Overwrite previous builds without asking
        "--clean", # Clean PyInstaller cache and remove temporary files before building
        "--onefile",
        "--distpath", str(DIST_DIR),
        str(entrypoint_full_path) # Use the full path here for PyInstaller
    ])
    logger.info("[DONE] EXE build complete.")

# --- Docker Builder ---
def build_docker(image_tag: str, entrypoint_script_relative: str):
    """
    Builds Docker image, generating a default Dockerfile if none exists.
    Requires entrypoint_script_relative to be relative to PROJECT_ROOT.
    """
    if not DOCKERFILE.is_file(): # Check is_file specifically
        logger.warning(f"Dockerfile not found at {DOCKERFILE}. Generating a default one.")
        # <<< START Dockerfile Generation >>>
        try:
            # Basic Dockerfile content - uses python:3.11-slim as a reasonable default
            # Assumes requirements.txt exists in PROJECT_ROOT
            # Uses the relative path of the entrypoint script passed in
            default_docker_content = f"""
# Auto-Generated Basic Python Dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements first to leverage Docker cache (if requirements.txt exists)
COPY requirements.txt .
# Use short-circuiting: install only if file exists, otherwise skip RUN
RUN if [ -f requirements.txt ]; then pip install --no-cache-dir -r requirements.txt; else echo "requirements.txt not found, skipping pip install."; fi

# Copy the rest of the application code from the project root
COPY . .

# Command to run the application using the provided entrypoint
CMD ["python", "{entrypoint_script_relative}"]
"""
            DOCKERFILE.write_text(default_docker_content.strip() + "\n", encoding='utf-8')
            logger.info(f"Generated default Dockerfile at: {DOCKERFILE}")
        except Exception as e:
            logger.error(f"[ERROR] Failed to generate default Dockerfile: {e}", exc_info=True)
            logger.warning("Skipping Docker build due to Dockerfile generation failure.")
            return # Don't proceed if we couldn't create the file
        # <<< END Dockerfile Generation >>>

    # Proceed with the build command if Dockerfile exists
    logger.info(f"[BUILD] Building Docker image: {image_tag}")
    # Pass PROJECT_ROOT as the build context directory (".")
    # Check=False because docker build might return non-zero for warnings
    # We should check the result object instead if stricter control is needed
    run_command(["docker", "build", "-t", image_tag, "."], cwd=PROJECT_ROOT, check=False)
    # Could add check here: e.g., run 'docker images -q {image_tag}' to verify creation
    logger.info("[DONE] Docker build attempt finished.")


# --- Main Entry ---
def main():
    parser = argparse.ArgumentParser(description="Build & Deploy Automation Tool")
    # Help text clarification
    parser.add_argument("--entrypoint", type=str,
                        help="Path to main script (relative to project root, e.g., 'src/main.py' or 'main.py')",
                        default=None)
    parser.add_argument("--skip-docker", action="store_true", help="Skip Docker image build")

    args = parser.parse_args()

    # Add arguments for docker_path, xwindows_path, and open_project
    parser.add_argument("--docker-path", type=str, default=None,
                        help="Optional: Path to the Docker executable.")
    parser.add_argument("--xwindows-path", type=str, default=None,
                        help="Optional: Path related to X Windows (specific use case needed).")
    parser.add_argument("--open-project", action="store_true",
                        help="Optional: Open the project after successful deployment.")

    # --- Determine entrypoint ---
    entrypoint_arg_value = args.entrypoint
    # Add logic to potentially read from config file if args.entrypoint is None
    # For now, rely only on args

    if not entrypoint_arg_value:
        # If still no entrypoint, exit
        logger.error("[FATAL] No entrypoint provided via --entrypoint argument.")
        sys.exit(1)

    # Assume entrypoint_arg_value is relative to PROJECT_ROOT
    # Construct full path for PyInstaller build
    entrypoint_full_path = PROJECT_ROOT / entrypoint_arg_value
    # Use the (potentially relative) path string for Dockerfile generation
    entrypoint_relative_path_str = entrypoint_arg_value

    # Basic validation if path exists relative to project root
    if not entrypoint_full_path.is_file():
        logger.warning(f"Entrypoint path '{entrypoint_full_path}' does not seem to exist or is not a file. Build might fail.")
        # Continue anyway, PyInstaller/Docker build will fail explicitly

    # Generate image tag from project directory name
    image_tag = PROJECT_ROOT.name.lower().replace(" ", "_").replace("-", "_")

    # --- Log Startup Info ---
    logger.info("=== Deploy Fusion Runner Starting ===")
    logger.info(f"Project Root: {PROJECT_ROOT}")
    logger.info(f"Entrypoint (relative): {entrypoint_relative_path_str}")
    logger.info(f"Entrypoint (full): {entrypoint_full_path}")
    logger.info(f"Docker Build: {'SKIPPED' if args.skip_docker else 'ENABLED'}")
    logger.info(f"Docker Path: {args.docker_path}")
    logger.info(f"X Windows Path: {args.xwindows_path}")
    logger.info(f"Open Project: {args.open_project}")

    # --- Build Steps ---
    build_exe(entrypoint_full_path)

    if not args.skip_docker:
        build_docker(image_tag, entrypoint_relative_path_str) # Pass relative path

    logger.info("=== Deployment Complete ===")

if __name__ == "__main__":
    main()