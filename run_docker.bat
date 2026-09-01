@echo off
setlocal enabledelayedexpansion

echo ===================================================
echo   AetherPhoenix AI Desktop Suite - Docker Launcher
echo ===================================================
echo.

set ROOT_DIR=%~dp0
cd /d "%ROOT_DIR%"

:: 1. Check if Docker CLI is installed
where docker >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker is not installed or not added to PATH.
    echo Please install Docker Desktop from https://www.docker.com/products/docker-desktop/
    pause
    exit /b 1
)

:: 2. Check if Docker daemon is running
docker info >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker daemon is not running!
    echo Please launch Docker Desktop and wait until it is fully initialized.
    pause
    exit /b 1
)

echo [1/3] Docker daemon is active and running.
echo.

:: 3. Check for existing local processes on ports 8000/5173
netstat -ano | findstr "LISTEN" | findstr ":8000 " >nul 2>&1
set PORT_8000_BUSY=!errorlevel!

netstat -ano | findstr "LISTEN" | findstr ":5173 " >nul 2>&1
set PORT_5173_BUSY=!errorlevel!

if "!PORT_8000_BUSY!"=="0" (
    echo [NOTICE] Port 8000 is currently occupied by local backend process.
)
if "!PORT_5173_BUSY!"=="0" (
    echo [NOTICE] Port 5173 is currently occupied by local frontend process.
)

echo.
echo Select action:
echo [1] Start Docker Containers ^(docker compose up --build -d^)
echo [2] Stop Docker Containers ^(docker compose down^)
echo [3] View Container Logs ^(docker compose logs -f^)
echo [4] Check Container Status ^(docker compose ps^)
echo.

set /p CHOICE="Enter choice [1-4] (default: 1): "
if "%CHOICE%"=="" set CHOICE=1

if "%CHOICE%"=="1" (
    echo.
    echo [2/3] Building and starting containers in detached mode...
    docker compose up --build -d
    if errorlevel 1 (
        echo [ERROR] Failed to start Docker containers.
        echo If ports 8000 or 5173 are occupied, stop local processes first.
        pause
        exit /b 1
    )
    echo.
    echo [3/3] Containers started successfully!
    docker compose ps
    echo.
    echo ===================================================
    echo   AetherPhoenix Docker Suite is running!
    echo   - Frontend: http://localhost:5173
    echo   - Backend API: http://localhost:8000
    echo   - Swagger Docs: http://localhost:8000/docs
    echo ===================================================
) else if "%CHOICE%"=="2" (
    echo Stopping and removing containers...
    docker compose down
) else if "%CHOICE%"=="3" (
    echo Displaying live container logs ^(Ctrl+C to exit^)...
    docker compose logs -f
) else if "%CHOICE%"=="4" (
    docker compose ps
)

echo.
pause
