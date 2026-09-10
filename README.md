# Build Deploy Run

A small desktop app that packages any Python project as a one-file Windows EXE (PyInstaller),
a Docker image, or both. It drops a self-contained build toolchain into the project so you can
rebuild from a batch file afterwards.

## Using the app

1. Run `dist\BuildDeployRun.exe` (or `launch.bat`).
2. Pick your project folder and its entrypoint script (for example `main.py` or `src\main.py`).
3. Choose a **Build target**: EXE + Docker image, EXE only, or Docker image only. Leave the
   Docker path empty unless Docker is installed somewhere unusual.
4. Click **Build Project**. The app:
   * copies `Build_Deploy_Run\` into your project (runner, workers, requirements),
   * creates `Build_Deploy_Run\.venv` with PyInstaller,
   * creates a project `.venv` if you do not have one,
   * writes `Build_Deploy_Run\.deploy_config` and `build_and_deploy_venv_locked.bat`,
   * packages the project (unless you untick **Package right after setup**).
5. The EXE lands in `<project>\dist\<entrypoint>.exe`; the Docker image is tagged
   `<project_name>:latest`. A failing step is reported in the log and in an error dialog.

Rebuild any time from your project folder:

```bat
.\Build_Deploy_Run\build_and_deploy_venv_locked.bat
```

The batch file reads its defaults (entrypoint and build target) from `.deploy_config`.
Arguments override them:

```bat
.\Build_Deploy_Run\build_and_deploy_venv_locked.bat src\main.py --skip-docker
```

Target flags: `--skip-docker` / `--docker` and `--skip-exe` / `--exe`.

If your project has a `requirements.txt`, it is installed into the tool venv before PyInstaller runs
so the EXE contains your dependencies. If it does not exist, one is generated from your project `.venv`.

A Docker build generates a default `Dockerfile` and `.dockerignore` only when the project has none.

## Headless mode

The same exe works without the GUI, which is handy for scripts and CI:

```bat
BuildDeployRun.exe --project C:\path\to\project --entrypoint src\main.py --skip-docker
```

Other flags: `--skip-exe` (Docker only), `--no-run` (set up only, no packaging), `--replace-venv`,
`--open-project`, `--docker-path`.

## Building the app from source

```bat
python -m pip install -r requirements.txt
python -m PyInstaller BuildDeployRun.spec --clean --noconfirm
```

To run the GUI from source instead: `python launch_gui.py`.

---

## ☕ Support the Project

If you find this project helpful and want to support further development by Fulllion Creative Works, consider leaving a tip!

* [Donate via PayPal](https://www.paypal.com/donate/?hosted_button_id=LCDZX75HR4CLC)
* [Support on Ko-fi](https://ko-fi.com/fulllion)

---
© 2026 Fulllion Creative Works. All rights reserved.
