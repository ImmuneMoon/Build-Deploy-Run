@echo off
:: ./launch_installer.bat
:: .bat launcher for the compiled GUI installer EXE

echo [*] Locating and launching BuildDeployRunInstaller.exe...
echo    (Ensure you have built the installer using PyInstaller first)
echo.

:: Get the directory where this batch file is located
set "BATCH_DIR=%~dp0"

:: Define the expected path to the executable relative to the batch file's location
set "EXE_PATH=%BATCH_DIR%dist\BuildDeployRunInstaller\BuildDeployRunInstaller.exe"

:: Check if the executable exists
if not exist "%EXE_PATH%" (
    echo [X] ERROR: Installer executable not found at:
    echo      %EXE_PATH%
    echo      Please build the project using 'pyinstaller build_installer.spec --clean'
    echo      in the main project directory (%BATCH_DIR%)
    pause
    exit /b 1
)

:: Launch the executable
echo [*] Starting: %EXE_PATH%
start "" "%EXE_PATH%"

echo.
echo [i] Installer GUI launched in a separate window.
echo     This window can be closed.
echo.
:: Optional: Pause if you want this window to stay open until manually closed
:: pause

exit /b 0