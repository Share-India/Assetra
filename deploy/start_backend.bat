@echo off
echo ==================================================
echo Starting FAR Backend (Single Worker Mode)
echo ==================================================
cd /d "%~dp0..\backend"
if not exist ".\venv2\Scripts\python.exe" (
    echo [ERROR] Virtual environment .\venv2\Scripts\python.exe not found!
    pause
    exit /b 1
)
echo [BACKEND] Running uvicorn with 1 worker on port 8001...
.\venv2\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8001 --workers 1
pause
