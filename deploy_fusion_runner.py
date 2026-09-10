# ./deploy_fusion_runner.py
"""
Build & Deploy runner.

Lives in <user_project>/Build_Deploy_Run/ and is executed by
build_and_deploy_venv_locked.bat with the Build_Deploy_Run/.venv interpreter.

Steps:
  1. Install the user project's requirements.txt into this venv (so PyInstaller
     can see the project's dependencies).
  2. Build a one-file EXE from the entrypoint into <user_project>/dist/.
  3. Unless --skip-docker: build a Docker image (generating a default Dockerfile
     and .dockerignore when the project has none).
"""

import argparse
import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path

from workers.run_command import run_command
from workers.logger_setup import setup_logger

# --- Paths ---
BDR_DIR = Path(__file__).resolve().parent          # <project>/Build_Deploy_Run
PROJECT_ROOT = BDR_DIR.parent                      # <project>
DIST_DIR = PROJECT_ROOT / "dist"
BUILD_DIR = PROJECT_ROOT / "build"
DOCKERFILE = PROJECT_ROOT / "Dockerfile"
DOCKERIGNORE = PROJECT_ROOT / ".dockerignore"
PROJECT_REQUIREMENTS = PROJECT_ROOT / "requirements.txt"

# Configure the root logger so output from workers.* (e.g. docker/PyInstaller stderr) reaches the log file too.
setup_logger(None, str(BDR_DIR / "logs" / "bdr_runner.log"))
logger = logging.getLogger("bdr_runner")

DEFAULT_DOCKER_PATHS = [
    # Docker Desktop, machine-wide install
    Path(r"C:\Program Files\Docker\Docker\resources\bin\docker.exe"),
    # Docker Desktop, per-user install (no admin rights)
    Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "DockerDesktop" / "resources" / "bin" / "docker.exe",
    Path("/usr/local/bin/docker"),
    Path("/usr/bin/docker"),
]


# --- Helpers ---
def resolve_entrypoint(entrypoint_arg: str):
    """Returns (full_path, path_relative_to_project_root) for the entrypoint."""
    candidate = Path(entrypoint_arg)
    full_path = candidate if candidate.is_absolute() else (PROJECT_ROOT / candidate)
    full_path = full_path.resolve()
    try:
        relative = full_path.relative_to(PROJECT_ROOT)
    except ValueError:
        logger.error(f"[FATAL] Entrypoint must live inside the project root {PROJECT_ROOT}: {full_path}")
        sys.exit(1)
    if not full_path.is_file():
        logger.error(f"[FATAL] Entrypoint is not a file: {full_path}")
        sys.exit(1)
    return full_path, relative


def find_docker(docker_path_arg):
    """Locate the docker executable: explicit arg, then PATH, then known install locations."""
    if docker_path_arg:
        candidate = Path(docker_path_arg)
        if candidate.is_file():
            return str(candidate)
        logger.warning(f"--docker-path given but not a file: {candidate}. Falling back to PATH lookup.")
    on_path = shutil.which("docker")
    if on_path:
        return on_path
    for candidate in DEFAULT_DOCKER_PATHS:
        if candidate.is_file():
            return str(candidate)
    return None


# --- Step 1: project requirements ---
def install_project_requirements() -> bool:
    if not PROJECT_REQUIREMENTS.is_file():
        logger.info("No project requirements.txt found; skipping dependency install.")
        return True
    logger.info(f"[DEPS] Installing project requirements from {PROJECT_REQUIREMENTS}")
    result = run_command(
        [sys.executable, "-m", "pip", "install", "-r", str(PROJECT_REQUIREMENTS)],
        cwd=PROJECT_ROOT, check=False,
    )
    if result.returncode != 0:
        logger.warning("[DEPS] Installing project requirements failed. The EXE may be missing modules.")
        return False
    logger.info("[DEPS] Project requirements installed.")
    return True


# --- Step 2: EXE ---
def build_exe(entrypoint_full_path: Path) -> bool:
    """Builds a single-file executable with PyInstaller. Returns True on success."""
    logger.info(f"[BUILD] Building EXE from: {entrypoint_full_path}")
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    BUILD_DIR.mkdir(parents=True, exist_ok=True)

    expected_exe = DIST_DIR / (entrypoint_full_path.stem + (".exe" if sys.platform == "win32" else ""))
    if expected_exe.exists():
        try:
            expected_exe.unlink()
        except OSError as e:
            logger.error(f"[BUILD] Cannot remove previous build {expected_exe}: {e}")
            return False

    result = run_command([
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--distpath", str(DIST_DIR),
        "--workpath", str(BUILD_DIR),
        "--specpath", str(BUILD_DIR),
        str(entrypoint_full_path),
    ], cwd=PROJECT_ROOT, check=False)

    if result.returncode != 0:
        logger.error(f"[BUILD] PyInstaller failed with exit code {result.returncode}.")
        return False
    if not expected_exe.is_file():
        logger.error(f"[BUILD] PyInstaller reported success but {expected_exe} was not produced.")
        return False
    logger.info(f"[DONE] EXE build complete: {expected_exe}")
    return True


# --- Step 3: Docker ---
def ensure_docker_files(entrypoint_relative: Path):
    """Generates a default Dockerfile and .dockerignore if the project has none."""
    if not DOCKERFILE.is_file():
        logger.warning(f"Dockerfile not found at {DOCKERFILE}. Generating a default one.")
        content = f"""# Auto-generated by Build_Deploy_Run. Edit freely; it will not be regenerated while it exists.
FROM python:3.11-slim

WORKDIR /app

# Install dependencies first so Docker can cache this layer.
COPY requirements.txt* ./
RUN if [ -f requirements.txt ]; then pip install --no-cache-dir -r requirements.txt; else echo "No requirements.txt, skipping pip install."; fi

# Copy the application code.
COPY . .

CMD ["python", "{entrypoint_relative.as_posix()}"]
"""
        DOCKERFILE.write_text(content, encoding="utf-8")
        logger.info(f"Generated default Dockerfile at: {DOCKERFILE}")

    if not DOCKERIGNORE.is_file():
        content = """# Auto-generated by Build_Deploy_Run.
Build_Deploy_Run/
.venv/
venv/
env/
dist/
build/
__pycache__/
*.pyc
.git/
*.spec
"""
        DOCKERIGNORE.write_text(content, encoding="utf-8")
        logger.info(f"Generated default .dockerignore at: {DOCKERIGNORE}")


def build_docker(image_tag: str, entrypoint_relative: Path, docker_exe: str) -> bool:
    """Builds the Docker image. Returns True if the image exists afterwards."""
    try:
        ensure_docker_files(entrypoint_relative)
    except Exception as e:
        logger.error(f"[DOCKER] Failed to generate Docker files: {e}", exc_info=True)
        return False

    logger.info(f"[BUILD] Building Docker image '{image_tag}' with {docker_exe}")
    # --load: with Docker Desktop's containerized BuildKit builder the result stays in the build cache
    # unless it is explicitly loaded into the local image store. Harmless with the classic builder.
    result = run_command([docker_exe, "build", "--load", "-t", image_tag, "."], cwd=PROJECT_ROOT, check=False)
    if result.returncode != 0:
        logger.error(f"[DOCKER] docker build failed with exit code {result.returncode}. Is Docker Desktop running?")
        return False

    verify = subprocess.run([docker_exe, "images", "-q", image_tag], capture_output=True, text=True)
    if not verify.stdout.strip():
        logger.error(f"[DOCKER] docker build finished but no image tagged '{image_tag}' was found.")
        return False
    logger.info(f"[DONE] Docker image built: {image_tag}")
    return True


# --- Main ---
def main():
    parser = argparse.ArgumentParser(description="Build & Deploy Automation Tool")
    parser.add_argument("--entrypoint", type=str, required=True,
                        help="Main script, relative to the project root (e.g. 'main.py' or 'src/main.py')")
    parser.add_argument("--skip-docker", action="store_true", help="Skip the Docker image build")
    parser.add_argument("--skip-exe", action="store_true", help="Skip the EXE build (Docker only)")
    parser.add_argument("--docker-path", type=str, default=None, help="Path to the docker executable")
    parser.add_argument("--xwindows-path", type=str, default=None, help="Path to VcXsrv (reserved for GUI containers)")
    parser.add_argument("--open-project", action="store_true", help="Reserved; handled by the installer")
    args = parser.parse_args()
    if args.skip_docker and args.skip_exe:
        parser.error("--skip-docker and --skip-exe together leave nothing to build.")

    entrypoint_full_path, entrypoint_relative = resolve_entrypoint(args.entrypoint)
    image_tag = PROJECT_ROOT.name.lower().replace(" ", "_").replace("-", "_") + ":latest"

    logger.info("=== Deploy Fusion Runner Starting ===")
    logger.info(f"Project Root:  {PROJECT_ROOT}")
    logger.info(f"Entrypoint:    {entrypoint_relative}")
    logger.info(f"Interpreter:   {sys.executable}")
    logger.info(f"EXE Build:     {'SKIPPED' if args.skip_exe else 'ENABLED'}")
    logger.info(f"Docker Build:  {'SKIPPED' if args.skip_docker else 'ENABLED'}")

    install_project_requirements()

    failures = []
    if not args.skip_exe and not build_exe(entrypoint_full_path):
        failures.append("EXE build")

    if not args.skip_docker:
        docker_exe = find_docker(args.docker_path)
        if not docker_exe:
            logger.error("[DOCKER] Docker executable not found (checked --docker-path, PATH, and default install "
                         "locations). Install Docker Desktop or re-run with --skip-docker.")
            failures.append("Docker build (docker not found)")
        elif not build_docker(image_tag, entrypoint_relative, docker_exe):
            failures.append("Docker build")

    if failures:
        logger.error(f"=== Deployment FAILED: {', '.join(failures)} ===")
        sys.exit(1)
    logger.info("=== Deployment Complete ===")


if __name__ == "__main__":
    main()
