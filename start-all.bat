@echo off
echo Starting Meta Knowledge Graph...
cd /d %~dp0

:: Start backend in new window
start "Backend Server" cmd /k "python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000"

:: Wait a moment
timeout /t 2 /nobreak > nul

:: Start frontend in new window
start "Frontend Server" cmd /k "cd frontend && npm run dev"

echo.
echo ====================================
echo  Backend:  http://localhost:8000
echo  Frontend: http://localhost:5173
echo  API Docs: http://localhost:8000/docs
echo ====================================
echo.
echo Press any key to close this window (servers will keep running)
pause > nul