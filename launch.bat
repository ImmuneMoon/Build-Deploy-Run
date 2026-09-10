@echo off
:: ./launch.bat
:: Launches the compiled Build Deploy Run app.

set "BATCH_DIR=%~dp0"
set "EXE_PATH=%BATCH_DIR%dist\BuildDeployRun.exe"

if not exist "%EXE_PATH%" (
    echo [X] ERROR: BuildDeployRun.exe not found at:
    echo      %EXE_PATH%
    echo      Build it first from the repo root with:
    echo      python -m PyInstaller BuildDeployRun.spec --clean --noconfirm
    pause
    exit /b 1
)

echo [*] Starting: %EXE_PATH%
start "" "%EXE_PATH%"
exit /b 0
