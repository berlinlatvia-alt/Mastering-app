@echo off
title 5.1 AutoMaster
cd /d "%~dp0"

:: Read old port and send graceful shutdown to ALL known ports
if exist .port (
    set /p OLD_PORT=<.port
    curl -s -X POST http://127.0.0.1:%OLD_PORT%/api/shutdown >nul 2>&1
)
:: Also try common ports in case .port file was stale
for /l %%p in (8000,1,8020) do (
    curl -s -X POST http://127.0.0.1:%%p/api/shutdown >nul 2>&1
)
timeout /t 2 /nobreak >nul

:: Force kill anything still on ports 8000-8099
for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr ":800" ^| findstr LISTENING') do (
    taskkill /F /PID %%a >nul 2>&1
)
timeout /t 1 /nobreak >nul

:: Delete old port file
if exist .port del .port

:: Start server in background (it writes .port when ready)
start /B python backend\main.py

:: Wait for .port file to appear (server is ready)
:wait
timeout /t 1 /nobreak >nul
if not exist .port goto wait

:: Read the port and open browser
set /p PORT=<.port
echo Server running on port %PORT%
start "" http://127.0.0.1:%PORT%
