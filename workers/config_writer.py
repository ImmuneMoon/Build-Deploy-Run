# workers/ config_writer.py

import json
import os

def write_env_from_config(config_path="user_config.json"):
    project_root = os.getcwd()
    env_path = os.path.join(project_root, ".env")

    try:
        with open(config_path, "r") as f:
            config = json.load(f)
    except FileNotFoundError:
        print("[X] user_config.json not found")
        exit(1)

    try:
        with open(env_path, "w") as f:
            f.write(f'EXE_PATH={config["exe_path"]}\n')
            f.write(f'DOCKER_IMAGE={config["docker_image"]}\n')
        print(f"[✓] .env written to {env_path}")
    except Exception as e:
        print(f"[X] Failed to write .env: {e}")
        exit(1)

if __name__ == "__main__":
    write_env_from_config()
