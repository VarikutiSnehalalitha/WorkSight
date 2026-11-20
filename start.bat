@echo off
title WorkSight Launcher
echo ==========================================================
echo    WorkSight — AI Workplace Intelligence & Attendance
echo ==========================================================
echo.
echo [1/2] Starting Backend FastAPI on http://localhost:8000...
start "WorkSight Backend" cmd /k "cd /d %~dp0backend && .venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"

timeout /t 3 /nobreak >nul

echo [2/2] Starting Frontend Next.js on http://localhost:3000...
start "WorkSight Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

echo.
echo WorkSight launched!
echo - Frontend: http://localhost:3000
echo - Backend:  http://localhost:8000/docs
echo.
pause
