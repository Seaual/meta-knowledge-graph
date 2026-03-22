@echo off
REM Start OpenClaw Web UI

echo Starting OpenClaw Web UI...

REM Start backend
echo Starting backend...
start cmd /k "cd backend && uvicorn main:app --reload --host 0.0.0.0 --port 8000"

REM Wait for backend
timeout /t 2 /nobreak > nul

REM Start frontend
echo Starting frontend...
start cmd /k "cd frontend && npm run dev"

echo.
echo OpenClaw Web UI is starting!
echo   Frontend: http://localhost:5173
echo   Backend:  http://localhost:8000
echo   API Docs: http://localhost:8000/docs
echo.
pause