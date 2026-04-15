batch
@echo off

:: ./build_and_deploy_venv_locked.bat

REM === Build & Deploy VENV Locked Script ===
SETLOCAL ENABLEEXTENSIONS
TITLE Build and Deploy - Locked Venv

REM --- Paths ---
SET VENV_DIR=%~dp0.venv
SET PYTHON_EXE=%VENV_DIR%\Scripts\python.exe
SET PROJECT_DIR=%~dp0..

REM --- Banner ---
echo -------------------------------------------------
echo  BUILD AND DEPLOY SCRIPT STARTED
echo  Using virtual environment: %VENV_DIR%
echo -------------------------------------------------
echo.

REM --- Check venv existence ---
IF NOT EXIST "%PYTHON_EXE%" (
    echo [FATAL] Python executable not found at: %PYTHON_EXE%
    echo         It’s likely your venv creation failed or is missing pip.
    echo         Try manually running:
    echo         python -m venv "%VENV_DIR%"
    echo         followed by:
    echo         "%VENV_DIR%\Scripts\python.exe" -m ensurepip
    where python
    pause
    exit /b 1
)

REM --- Debug global Python paths ---
echo [DEBUG] Checking global python paths:
where python

REM --- Activate Environment ---
call "%VENV_DIR%\Scripts\activate.bat"

REM --- Determine Entrypoint from Command Line ---
SET ENTRYPOINT_TO_USE=
SET SKIP_DOCKER_ARG=

REM Check if the first argument (entrypoint) is provided
IF "%~1"=="" (
    echo [FATAL] Error: No entrypoint script path provided.
    echo Usage: %~nx0 ^<entrypoint_script_path^> [optional_args]
    echo Example: %~nx0 src\main.py
    pause
    exit /b 1
) ELSE (
    SET ENTRYPOINT_TO_USE=%~1
)

REM Process other optional arguments if needed (e.g., --skip-docker)
REM This part would need to be expanded if you have more optional args
IF /I "%~2"=="--skip-docker" (
    SET SKIP_DOCKER_ARG=--skip-docker
)


REM --- Set ENTRYPOINT_ARG for deploy_fusion_runner.py ---
REM Enclose in quotes to handle paths with spaces
SET ENTRYPOINT_ARG=--entrypoint "%ENTRYPOINT_TO_USE%"

REM --- Run Deployment ---
echo [INFO] Launching deployment...
"%PYTHON_EXE%" -c "import runpy; runpy.run_path(r'%~dp0internal\\deploy_fusion_runner.py', run_name='__main__')" %ENTRYPOINT_ARG% %SKIP_DOCKER_ARG%

REM --- Freeze Dependencies ---
echo [INFO] Freezing requirements.txt to project root
"%PYTHON_EXE%" -m pip freeze > "%PROJECT_DIR%\requirements.txt"

echo.
echo [SUCCESS] Build and deploy process complete.
pause
exit /b 0
