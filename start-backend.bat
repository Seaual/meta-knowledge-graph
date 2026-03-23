@echo off
echo Starting Meta Knowledge Graph Backend...
cd /d %~dp0
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
pause