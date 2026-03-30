@echo off
chcp 65001 >nul
echo ========================================
echo   Meta Knowledge Graph
echo ========================================
echo.

:: Check if venv exists
if not exist "venv\Scripts\activate.bat" (
    echo [ERROR] Python virtual environment not found!
    echo Please run: python -m venv venv
    pause
    exit /b 1
)

:: Check if node_modules exists
if not exist "frontend\node_modules" (
    echo [ERROR] Frontend dependencies not installed!
    echo Please run: cd frontend && npm install
    pause
    exit /b 1
)

echo [1/2] Starting backend server...
start "Backend" cmd /k "venv\Scripts\activate.bat && python -m uvicorn backend.main:app --host 0.0.0.0 --port 8089"

echo [2/2] Starting frontend server...
cd frontend
start "Frontend" cmd /k "npm run dev"
cd ..

echo.
echo ========================================
echo   Backend:  http://localhost:8089
echo   Frontend: http://localhost:5173
echo   API Docs: http://localhost:8089/docs
echo ========================================
echo.
echo Press any key to exit this window...
pause >nul