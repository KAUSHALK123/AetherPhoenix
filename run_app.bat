@echo off
echo Starting AetherPhoenix Test and Build Pipeline...

echo ----------------------------------------
echo Backend Setup and Testing
echo ----------------------------------------
cd backend
call uv sync
set PYTHONPATH=..
call uv run pytest
call uv run ruff check .
call uv run black --check .
if %errorlevel% neq 0 (
    echo Backend checks failed!
    exit /b %errorlevel%
)

echo ----------------------------------------
echo Frontend Build
echo ----------------------------------------
cd ../frontend
call npm install
call npm run build
if %errorlevel% neq 0 (
    echo Frontend build failed!
    exit /b %errorlevel%
)

echo ----------------------------------------
echo Docker Compose Setup
echo ----------------------------------------
cd ..
docker compose build
docker compose up -d

echo ----------------------------------------
echo Docker Services Status
echo ----------------------------------------
docker compose ps

echo ----------------------------------------
echo Press any key to bring down the services...
echo ----------------------------------------
pause
docker compose down
