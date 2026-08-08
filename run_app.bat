@echo off
echo Starting AetherPhoenix Development Environment...

echo Starting Backend...
start "Backend" cmd /k "cd backend && uv run uvicorn app.main:app --reload"

echo Starting Frontend...
start "Frontend" cmd /k "cd frontend && npm install && npm run dev"

echo Both services are starting in separate windows.
pause
