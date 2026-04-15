# workers/ build_fusion.py

import json, subprocess, sys,shutil
from pathlib import Path
# Attempt to import the existing docker helper
try:
    from . import docker_helpers
    HAS_DOCKER_HELPER = True
except ImportError:
    print("[!] Warning: Could not import docker_helpers. Using basic Docker command.")
    HAS_DOCKER_HELPER = False

def load_config(config_path: Path):
    """Loads configuration from the specified JSON file."""
    if not config_path.exists():
        raise FileNotFoundError(f"[!] Config file not found: {config_path}")
    try:
        with open(config_path, "r", encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"[!] Error decoding JSON from {config_path}: {e}")
    except Exception as e:
        raise RuntimeError(f"[!] Failed to read config file {config_path}: {e}")

def build_exe(entry_point: str, project_dir: Path, dist_path: Path):
    """Builds an executable using PyInstaller."""
    print(f"[•] Building EXE from: {entry_point}")
    build_path = project_dir / "build" # PyInstaller's build cache
    # Ensure build path exists for spec file, clean not always sufficient
    build_path.mkdir(exist_ok=True) 
    
    try:
        subprocess.run([
            sys.executable, "-m", "PyInstaller", # Use python -m PyInstaller
            "--onefile",
            "--clean", # Clean PyInstaller cache and files
            "--distpath", str(dist_path),
            "--workpath", str(build_path), # Use project-level build folder
            "--specpath", str(build_path), # Place .spec file in build folder
            entry_point
        ], check=True, capture_output=True, text=True) # Capture output
        print("[✓] EXE build complete.")
    except subprocess.CalledProcessError as e:
        print(f"[X] PyInstaller failed with exit code {e.returncode}")
        print(f"----- PyInstaller STDOUT -----")
        print(e.stdout)
        print(f"----- PyInstaller STDERR -----")
        print(e.stderr)
        print(f"----------------------------")
        raise RuntimeError("PyInstaller build failed.") # Re-raise after printing details
    except FileNotFoundError:
        print("[X] Error: 'pyinstaller' command not found. Is it installed in the venv?")
        raise
    except Exception as e:
        print(f"[X] An unexpected error occurred during PyInstaller build: {e}")
        raise


def build_docker_image_wrapper(project_dir: Path, config: dict):
    """Builds a Docker image, optionally using the docker_helpers module."""
    dockerfile = project_dir / "Dockerfile"
    if not dockerfile.exists():
        print("[i] No Dockerfile found. Skipping Docker build.")
        return

    # Use tag from config if available, otherwise generate default
    default_tag = project_dir.name.lower().replace(" ", "_") + ":latest"
    tag = config.get("docker_tag", default_tag)

    print(f"[•] Attempting to build Docker image: {tag}")

    if HAS_DOCKER_HELPER:
        print("[i] Using docker_helpers module.")
        try:
            # Ensure docker is found first (helper function)
            if docker_helpers.check_docker_installed():
                docker_helpers.build_docker_image(str(project_dir), tag) # Pass project_dir as string
                print(f"[✓] Docker image '{tag}' build successful (via helper).")
            else:
                 print("[X] Docker helper reported Docker is not installed/found.")
                 raise RuntimeError("Docker not found by helper.")
        except Exception as e:
            print(f"[X] Docker build failed using helper: {e}")
            # Optionally fall back to basic command? Or just fail? Let's fail for now.
            raise
    else:
        # Fallback if docker_helpers import failed
        print("[i] Using basic subprocess command for Docker build.")
        try:
            subprocess.run(["docker", "build", "-t", tag, "."], cwd=project_dir, check=True)
            print(f"[✓] Docker image '{tag}' build successful (via basic command).")
        except FileNotFoundError:
             print("[X] Error: 'docker' command not found. Is Docker installed and in PATH?")
             raise
        except subprocess.CalledProcessError as e:
            print(f"[X] Docker build failed: {e}")
            raise # Re-raise the error
        except Exception as e:
            print(f"[X] An unexpected error occurred during Docker build: {e}")
            raise

def clean_directory(dir_path: Path):
    """Removes all files and subdirectories within a directory."""
    if not dir_path.is_dir():
        return
    print(f"[•] Cleaning directory: {dir_path}")
    for item in dir_path.iterdir():
        try:
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()
        except Exception as e:
            print(f"[!] Warning: Could not remove {item}: {e}")


def main():
    # Determine paths relative to this script's location
    script_path = Path(__file__).resolve()
    # Assumes this script is in Build_Deploy_Run/workers/
    workers_dir = script_path.parent
    bdr_path = workers_dir.parent # Build_Deploy_Run folder
    project_dir = bdr_path.parent # User's project root

    config_filename = "bdr_config.json" # Use the name saved by the installer
    config_path = bdr_path / config_filename
    dist_path = project_dir / "dist"
    build_path = project_dir / "build" # PyInstaller build cache

    print(f"--- Starting Build Fusion ---")
    print(f"Project Directory: {project_dir}")
    print(f"BuildDeployRun Directory: {bdr_path}")
    print(f"Config File: {config_path}")
    print(f"Dist Output Path: {dist_path}")
    print(f"Build Cache Path: {build_path}")
    print(f"---------------------------")

    try:
        config = load_config(config_path)
        print(f"[i] Loaded config: {config}")

        # Determine entry point from config, default to main.py in project root
        entry_point_relative = config.get("entry_point", "main.py")
        entry_point_absolute = project_dir / entry_point_relative

        if not entry_point_absolute.exists():
            raise FileNotFoundError(f"[!] Entrypoint script not found: {entry_point_absolute} (relative: {entry_point_relative})")
        print(f"[i] Using entrypoint: {entry_point_absolute}")

        # Clean old distribution and build directories
        clean_directory(dist_path)
        # build_path is cleaned by PyInstaller's --clean flag, but create if not exists
        dist_path.mkdir(exist_ok=True)
        build_path.mkdir(exist_ok=True)

        # --- Build Steps ---
        # 1. Build EXE
        build_exe(str(entry_point_absolute), project_dir, dist_path)

        # 2. Build Docker if available
        build_docker_image_wrapper(project_dir, config)

        print("\n[✓] Build Fusion finished successfully.")

    except FileNotFoundError as e:
        print(f"\n[X] ERROR: A required file was not found: {e}")
        sys.exit(1)
    except ValueError as e:
         print(f"\n[X] ERROR: Configuration error: {e}")
         sys.exit(1)
    except RuntimeError as e:
        print(f"\n[X] ERROR: Build process failed: {e}")
        sys.exit(1)
    except Exception as e:
        import traceback
        print(f"\n[X] An unexpected critical error occurred: {e}")
        print(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    # This script expects to be run from within the project's virtual environment
    # by deploy_fusion_runner.py
    main()