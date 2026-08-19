@echo off
setlocal enabledelayedexpansion

echo ===================================================
echo   AetherPhoenix AI Desktop Suite - Launch Script
echo ===================================================
echo.

set ROOT_DIR=%~dp0
set BACKEND_DIR=%ROOT_DIR%backend
set FRONTEND_DIR=%ROOT_DIR%frontend

:: 1. Launch Backend API Server
echo [1/3] Starting FastAPI Backend on http://localhost:8000...
cd /d "%BACKEND_DIR%"
set PYTHONPATH=%ROOT_DIR%

if exist ".venv\Scripts\uvicorn.exe" (
    start "AetherPhoenix Backend" /min cmd /c "set PYTHONPATH=%ROOT_DIR%&& .venv\Scripts\uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"
) else (
    start "AetherPhoenix Backend" /min cmd /c "set PYTHONPATH=%ROOT_DIR%&& python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"
)

:: 2. Launch Frontend Dev Server
echo [2/3] Starting Vite Frontend on http://localhost:5173...
cd /d "%FRONTEND_DIR%"
start "AetherPhoenix Frontend" /min cmd /c "npm run dev"

:: 3. Open Browser
echo [3/3] Launching AetherPhoenix in browser...
timeout /t 3 /nobreak >nul
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
