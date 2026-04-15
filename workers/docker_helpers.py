# workers/ docker_helpers.py

import os
import subprocess
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

def get_docker_path():
    """
    Gets the path to the Docker executable.

    Returns:
        Path: The path to the Docker executable, or None if not found.
    """
    # Check for environment variable
    docker_path = os.environ.get("DOCKER_PATH")
    if docker_path:
        docker_path = Path(docker_path)
        if docker_path.exists():
            return docker_path
        else:
            logger.warning("DOCKER_PATH environment variable is set, but the path is invalid.")

    # Default locations (consider adding more)
    default_paths = [
        Path("C:/Program Files/Docker/Docker/resources/bin/docker.exe"),  # Windows
        Path("/usr/local/bin/docker"),  # macOS/Linux
        Path("/usr/bin/docker"),
    ]
    for path in default_paths:
        if path.exists():
            return path
    return None



def check_docker_installed():
    """
    Checks if Docker is installed and available in the system's PATH.
    Returns:
        bool: True if Docker is installed, False otherwise.
    """
    docker_path = get_docker_path()
    if docker_path:
        return True
    else:
        return False


def build_docker_image(project_dir, tag="super_power_options"):
    """
    Builds the Docker image.

    Args:
        project_dir (str): The path to the project directory.
        tag (str, optional): The tag for the Docker image. Defaults to "super_power_options".
    """
    if not check_docker_installed():
        logger.error("Docker is not installed or not in PATH.")
        raise RuntimeError("Docker is not installed or not in PATH.")

    logger.info(f"Building Docker image with tag: {tag}")
    try:
        subprocess.run(["docker", "build", "-t", tag, project_dir], check=True)
        logger.info("Docker image built successfully.")
    except subprocess.CalledProcessError as e:
        logger.error(f"Error building Docker image: {e}")
        raise  # Re-raise the exception to be handled by the caller

def run_docker_container(tag="super_power_options", port=8000):
    """
    Runs the Docker container.

    Args:
        tag (str, optional): The tag of the Docker image to run. Defaults to "super_power_options".
        port (int, optional): The port to expose. Defaults to 8000.
    """
    if not check_docker_installed():
        logger.error("Docker is not installed or not in PATH.")
        raise RuntimeError("Docker is not installed or not in PATH.")
    logger.info(f"Running Docker container from image: {tag}, exposing port: {port}")
    try:
        subprocess.run(["docker", "run", "-p", f"{port}:{port}", tag], check=True)
        logger.info("Docker container running.")
    except subprocess.CalledProcessError as e:
        logger.error(f"Error running Docker container: {e}")
        raise

def stop_docker_container(tag="super_power_options"):
    """
    Stops the Docker container.

    Args:
        tag (str, optional):The tag of the docker image to stop
    """
    if not check_docker_installed():
        logger.error("Docker is not installed or not in PATH.")
        raise RuntimeError("Docker is not installed or not in PATH.")
    logger.info(f"Stopping Docker container with image name: {tag}")
    try:
        # Get the container ID first
        container_id_process = subprocess.run(["docker", "ps", "-q", "-f", f"ancestor={tag}"],
                                             check=True, capture_output=True, text=True)
        container_id = container_id_process.stdout.strip()

        if container_id:
            subprocess.run(["docker", "stop", container_id], check=True)
            logger.info("Docker container stopped")
        else:
            logger.warning(f"No running container found for image: {tag}")
    except subprocess.CalledProcessError as e:
        logger.error(f"Error stopping Docker container: {e}")
        raise
        
def remove_docker_image(tag="super_power_options"):
    """
    Removes the docker image

    Args:
        tag (str): The tag of the image to remove
    """
    if not check_docker_installed():
        logger.error("Docker is not installed or not in PATH.")
        raise RuntimeError("Docker is not installed or not in PATH.")
    logger.info(f"Removing docker image: {tag}")
    try:
        subprocess.run(["docker", "image", "remove", tag], check=True)
        logger.info("Docker image removed")
    except subprocess.CalledProcessError as e:
        logger.error(f"Error removing docker image: {e}")
        raise

if __name__ == "__main__":
    # Example usage
    project_dir = "."  # Replace with your actual project directory
    tag_name = "my_app_image"
    try:
        build_docker_image(project_dir, tag_name)
        run_docker_container(tag_name)
        # Add a delay
        import time
        time.sleep(10)
        stop_docker_container(tag_name)
        remove_docker_image(tag_name)
    except Exception as e:
        logger.error(f"An error occurred: {e}")