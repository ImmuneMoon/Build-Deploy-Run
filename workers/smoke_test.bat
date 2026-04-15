@echo off
:: ./workers/smoke_test.bat
setlocal enabledelayedexpansion

echo.
echo [*] Starting Smoke Test...
echo.

REM === Change to project root ===
cd /d %~dp0\..

REM === Write .env from user_config.json ===
echo [*] Generating .env from user_config.json...
python Build_Deploy_Run\workers\config_writer.py

REM === If Python failed to run, abort
if errorlevel 1 (
    echo [X] Python failed to generate .env — aborting.
    pause
    exit /b
)

REM === If .env file somehow still missing, abort
if not exist ".env" (
    echo [X] .env file not found after Python execution — aborting.
    pause
    exit /b
)


REM === EXE Smoke Test ===
echo [DEBUG] Checking for EXE at: !EXE_PATH!

if exist "!EXE_PATH!" (
    echo [*] Testing EXE...
    "!EXE_PATH!" --help >nul 2>&1
    if !errorlevel! == 0 (
        echo [✓] EXE launched successfully.
    ) else (
        echo [X] EXE failed to launch.
    )
) else (
    echo [!] "!EXE_PATH!" not found — skipping EXE test.
)

echo.

REM === Docker Smoke Test ===
echo [*] Testing Docker image: !DOCKER_IMAGE!...

docker run --rm "!DOCKER_IMAGE!" --help >nul 2>&1
if !errorlevel! == 0 (
    echo [✓] Docker container ran successfully.
) else (
    echo [X] Docker container failed.
)

echo.
pause
