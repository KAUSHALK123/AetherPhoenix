@echo off
setlocal enabledelayedexpansion

echo ===================================================
echo   AetherPhoenix AI Desktop Suite - Launch Script
echo ===================================================
echo.

set ROOT_DIR=%~dp0
set BACKEND_DIR=%ROOT_DIR%backend
set FRONTEND_DIR=%ROOT_DIR%frontend
set PY_CMD=python

where py >nul 2>&1
if not errorlevel 1 (
    py -3.13 --version >nul 2>&1
    if not errorlevel 1 set "PY_CMD=py -3.13"
)

:: 0. Ensure dependencies exist
cd /d "%BACKEND_DIR%"
if not exist ".venv\Scripts\python.exe" (
    echo [0/4] Creating backend Python virtual environment with %PY_CMD%...
    %PY_CMD% -m venv .venv
    if errorlevel 1 (
        echo Failed to create backend virtual environment.
        exit /b 1
    )
)

if not exist ".venv\Scripts\pip.exe" (
    echo [0/4] Bootstrapping pip inside the backend virtual environment...
    ".venv\Scripts\python.exe" -m ensurepip --upgrade
    if errorlevel 1 (
        echo Failed to bootstrap pip.
        exit /b 1
    )
)

call ".venv\Scripts\activate.bat"
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo Failed to install backend dependencies.
    exit /b 1
)

cd /d "%FRONTEND_DIR%"
if not exist "node_modules" (
    echo [0/4] Installing frontend dependencies...
    call npm install
    if errorlevel 1 (
        echo Failed to install frontend dependencies.
        exit /b 1
    )
) else (
    echo [0/4] Frontend dependencies already installed.
)

:: 1. Launch Backend API Server
echo [1/3] Starting FastAPI Backend on http://localhost:8000...
cd /d "%BACKEND_DIR%"
if exist ".venv\Scripts\uvicorn.exe" (
    start "AetherPhoenix Backend" /min cmd /c "set PYTHONPATH=%ROOT_DIR%;%BACKEND_DIR%&& .venv\Scripts\uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"
) else (
    start "AetherPhoenix Backend" /min cmd /c "set PYTHONPATH=%ROOT_DIR%;%BACKEND_DIR%&& python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"
)

:: 2. Launch Frontend Dev Server
echo [2/3] Starting Vite Frontend on http://localhost:5173...
cd /d "%FRONTEND_DIR%"
start "AetherPhoenix Frontend" /min cmd /c "npm run dev -- --host 0.0.0.0 --port 5173"

:: 3. Open Browser
echo [3/3] Launching AetherPhoenix in browser...
timeout /t 10 /nobreak >nul
start http://localhost:5173

echo.
echo ===================================================
echo   AetherPhoenix is running!
echo   - Frontend: http://localhost:5173
echo   - Backend API: http://localhost:8000
echo   - Swagger Docs: http://localhost:8000/docs
echo ===================================================
echo.
echo Press any key to close this launcher window (services will remain running)...
pause >nul
