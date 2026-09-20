@echo off
setlocal enabledelayedexpansion

echo ===================================================
echo   AetherPhoenix AI Desktop Suite - Launcher
echo ===================================================
echo.

set ROOT_DIR=%~dp0
cd /d "%ROOT_DIR%"

echo Select launch environment:
echo   [1] Docker  (Run full stack in Docker containers) [Default]
echo   [2] Local   (Python venv + Vite dev server)
echo   [3] Stop Docker Containers
echo   [4] View Docker Logs
echo.

set /p CHOICE="Enter choice [1-4] (default: 1): "
if "%CHOICE%"=="" set CHOICE=1

if "%CHOICE%"=="1" goto RUN_DOCKER
if "%CHOICE%"=="2" goto RUN_LOCAL
if "%CHOICE%"=="3" goto STOP_DOCKER
if "%CHOICE%"=="4" goto LOGS_DOCKER

echo Invalid choice. Defaulting to Docker...
goto RUN_DOCKER

:RUN_DOCKER
echo.
echo ---------------------------------------------------
echo   Launching via Docker
echo ---------------------------------------------------

:: 1. Check if Docker CLI is installed
where docker >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker is not installed or not added to PATH.
    echo Please install Docker Desktop from https://www.docker.com/products/docker-desktop/
    echo or choose Option 2 to run locally without Docker.
    echo.
    pause
    exit /b 1
)

:: 2. Check if Docker daemon is running
docker info >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker daemon is not running!
    echo Please launch Docker Desktop and wait until it is fully initialized,
    echo then run this script again.
    echo.
    pause
    exit /b 1
)

echo [1/3] Docker daemon is active and running.
echo [2/3] Building and starting containers in background (docker compose up --build -d)...
docker compose up --build -d
if errorlevel 1 (
    echo [ERROR] Failed to start Docker containers.
    pause
    exit /b 1
)

echo.
echo [3/3] Containers started successfully!
docker compose ps
echo.
timeout /t 3 /nobreak >nul
start http://localhost:5173

echo ===================================================
echo   AetherPhoenix is running via Docker!
echo   - Frontend:    http://localhost:5173
echo   - Backend API: http://localhost:8000
echo   - API Docs:    http://localhost:8000/docs
echo ===================================================
echo.
echo Tip: To stop containers later, run this script and choose Option 3.
echo.
pause
exit /b 0

:STOP_DOCKER
echo.
echo Stopping and removing Docker containers...
docker compose down
echo Docker containers stopped.
pause
exit /b 0

:LOGS_DOCKER
echo.
echo Displaying live Docker container logs (Ctrl+C to exit)...
docker compose logs -f
pause
exit /b 0

:RUN_LOCAL
echo.
echo ---------------------------------------------------
echo   Launching Locally (Virtualenv + Vite)
echo ---------------------------------------------------

set BACKEND_DIR=%ROOT_DIR%backend
set FRONTEND_DIR=%ROOT_DIR%frontend
set PY_CMD=python

where py >nul 2>&1
if not errorlevel 1 (
    py -3.13 --version >nul 2>&1
    if not errorlevel 1 set "PY_CMD=py -3.13"
)

:: Ensure backend virtual environment and dependencies
cd /d "%BACKEND_DIR%"
if not exist ".venv\Scripts\python.exe" (
    echo [0/4] Creating backend Python virtual environment with %PY_CMD%...
    %PY_CMD% -m venv .venv
    if errorlevel 1 (
        echo Failed to create backend virtual environment.
        pause
        exit /b 1
    )
)

if not exist ".venv\Scripts\pip.exe" (
    echo [0/4] Bootstrapping pip inside the backend virtual environment...
    ".venv\Scripts\python.exe" -m ensurepip --upgrade
    if errorlevel 1 (
        echo Failed to bootstrap pip.
        pause
        exit /b 1
    )
)

call ".venv\Scripts\activate.bat"
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo Failed to install backend dependencies.
    pause
    exit /b 1
)

:: Ensure frontend dependencies
cd /d "%FRONTEND_DIR%"
if not exist "node_modules" (
    echo [0/4] Installing frontend dependencies...
    call npm install
    if errorlevel 1 (
        echo Failed to install frontend dependencies.
        pause
        exit /b 1
    )
) else (
    echo [0/4] Frontend dependencies already installed.
)

:: Launch Backend
echo [1/3] Starting FastAPI Backend on http://localhost:8000...
cd /d "%BACKEND_DIR%"
if exist ".venv\Scripts\uvicorn.exe" (
    start "AetherPhoenix Backend" /min cmd /c "set PYTHONPATH=%ROOT_DIR%;%BACKEND_DIR%&& .venv\Scripts\uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"
) else (
    start "AetherPhoenix Backend" /min cmd /c "set PYTHONPATH=%ROOT_DIR%;%BACKEND_DIR%&& python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"
)

:: Launch Frontend
echo [2/3] Starting Vite Frontend on http://localhost:5173...
cd /d "%FRONTEND_DIR%"
start "AetherPhoenix Frontend" /min cmd /c "npm run dev -- --host 0.0.0.0 --port 5173"

:: Open Browser
echo [3/3] Launching AetherPhoenix in browser...
timeout /t 5 /nobreak >nul
start http://localhost:5173

echo.
echo ===================================================
echo   AetherPhoenix is running locally!
echo   - Frontend:    http://localhost:5173
echo   - Backend API: http://localhost:8000
echo   - API Docs:    http://localhost:8000/docs
echo ===================================================
echo.
echo Press any key to close this launcher window (services will remain running)...
pause >nul
exit /b 0
