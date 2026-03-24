@echo off
REM 5.1 AutoMaster - Startup Script
REM DOGE Mode: Silent boot, fail-fast

echo Starting 5.1 AutoMaster...

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python 3.10+
    pause
    exit /b 1
)

REM Check dependencies
echo Checking dependencies...
pip show fastapi >nul 2>&1
if errorlevel 1 (
    echo Installing dependencies...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] Failed to install dependencies
        pause
        exit /b 1
    )
)

REM Check FFmpeg
where ffmpeg >nul 2>&1
if errorlevel 1 (
    echo [WARN] FFmpeg not found in PATH. Some features may not work.
    echo Download from: https://ffmpeg.org/download.html
)

REM Start server
echo.
echo ========================================
echo   5.1 AutoMaster - Suno to Surround
echo ========================================
echo.

cd /d "%~dp0"

:: Delete old port file
if exist .port del .port

:: Start server in background (it writes .port when ready)
start /B python backend\main.py

:: Wait for .port file (server is ready)
:wait
timeout /t 1 /nobreak >nul
if not exist .port goto wait

:: Read port and open browser
set /p PORT=<.port
echo Server running on http://127.0.0.1:%PORT%
start "" http://127.0.0.1:%PORT%

pause
