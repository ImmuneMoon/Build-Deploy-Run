# install_config/config.py
from pathlib import Path

# Base directory of the project.  Use Path for robust path manipulation.
BASE_DIR = Path(__file__).resolve().parent.parent

# Configuration settings
CONFIG = {
    "BASE_DIR": str(BASE_DIR),  # Store as string for consistency
    "LOG_DIR": str(BASE_DIR / "logs"),
    "SETTINGS_DIR": str(BASE_DIR / "settings"),
    "TEMP_DIR": str(BASE_DIR / "temp"),
    "BUILD_DIR": str(BASE_DIR / "build"),
    "XINFERENCE_DIR": str(BASE_DIR / "xinference"),
    "DEPLOY_DIR": str(BASE_DIR / "deploy"),
    "MODEL_DIR": str(BASE_DIR / "models"),
    "DATA_DIR": str(BASE_DIR / "data"),
}

# Ensure directories exist
for path_str in [CONFIG["LOG_DIR"], CONFIG["SETTINGS_DIR"], CONFIG["TEMP_DIR"], CONFIG["BUILD_DIR"], CONFIG["DEPLOY_DIR"]]:
    path = Path(path_str)
    path.mkdir(parents=True, exist_ok=True)  # Use pathlib's mkdir

if __name__ == "__main__":
    # Example of how to use the configuration
    print(f"Base Directory: {CONFIG['BASE_DIR']}")
    print(f"Log Directory: {CONFIG['LOG_DIR']}")
    print(f"Settings Directory: {CONFIG['SETTINGS_DIR']}")
    print(f"Temp Directory: {CONFIG['TEMP_DIR']}")
    print(f"Build Directory: {CONFIG['BUILD_DIR']}")
    print(f"Deploy Directory: {CONFIG['DEPLOY_DIR']}")
