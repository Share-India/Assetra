@echo off
setlocal enabledelayedexpansion

echo ==================================================
echo Starting FAR Replacement Value Calculator
echo ==================================================
echo.

:: 1. Start Backend in a new window with exactly 1 worker
echo [STARTUP] Starting FastAPI backend with 1 worker...
start "FAR Backend Server (1 Worker)" cmd /c "cd /d %~dp0..\backend && .\venv2\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8001 --workers 1"

:: 2. Wait for Backend Health
echo [STARTUP] Waiting for backend to become healthy on port 8001...
set "HEALTH_URL=http://127.0.0.1:8001/health"
set "MAX_RETRIES=20"
set "RETRY_COUNT=0"

:CHECK_HEALTH
powershell -Command "try { $response = Invoke-RestMethod -Uri '%HEALTH_URL%' -Method Get -ErrorAction Stop; if ($response.status -eq 'ok') { exit 0 } else { exit 1 } } catch { exit 1 }"
if %ERRORLEVEL% EQU 0 (
    echo [STARTUP] Backend is healthy!
    goto START_FRONTEND
)

set /a RETRY_COUNT+=1
if !RETRY_COUNT! GEQ %MAX_RETRIES% (
    echo [ERROR] Backend failed to start or did not become healthy within the timeout limit.
    echo Please inspect the backend console window and backend\app.log for details.
    pause
    exit /b 1
)

timeout /t 2 /nobreak >nul
goto CHECK_HEALTH

:START_FRONTEND
:: 3. Start Frontend in a new window
echo [STARTUP] Starting React frontend (Vite)...
start "FAR Frontend Server" cmd /c "cd /d %~dp0..\frontend && npm run dev"

echo.
echo ==================================================
echo SUCCESS: FAR Calculator started!
echo Frontend: http://localhost:3000
echo Backend:  http://127.0.0.1:8001
echo ==================================================
echo.
pause
