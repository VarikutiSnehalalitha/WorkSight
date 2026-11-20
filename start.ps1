# WorkSight Local Development Launcher
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "   WorkSight — AI Workplace Intelligence & Attendance    " -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Cyan

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# 1. Start Backend FastAPI Server
Write-Host "`n[1/2] Starting FastAPI Backend on http://localhost:8000..." -ForegroundColor Yellow
$backendJob = Start-Process -FilePath "$scriptDir\backend\.venv\Scripts\python.exe" `
    -ArgumentList "-m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload" `
    -WorkingDirectory "$scriptDir\backend" `
    -PassThru

Start-Sleep -Seconds 3

# 2. Start Frontend Next.js Server
Write-Host "`n[2/2] Starting Next.js Frontend on http://localhost:3000..." -ForegroundColor Yellow
$frontendJob = Start-Process -FilePath "npm" `
    -ArgumentList "run dev -- --port 3000" `
    -WorkingDirectory "$scriptDir\frontend" `
    -PassThru

Write-Host "`n==========================================================" -ForegroundColor Cyan
Write-Host "WorkSight is running!" -ForegroundColor Green
Write-Host " - Frontend UI: http://localhost:3000" -ForegroundColor White
Write-Host " - Backend API: http://localhost:8000/docs" -ForegroundColor White
Write-Host " - Demo Logins: (Password for all: WorkSight2026!)" -ForegroundColor White
Write-Host "     Super Admin:  owner@worksight.io" -ForegroundColor Gray
Write-Host "     HR Admin:     hr@worksight.io" -ForegroundColor Gray
Write-Host "     Dept Manager: manager@worksight.io" -ForegroundColor Gray
Write-Host "     Employee:     employee@worksight.io" -ForegroundColor Gray
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "Press Ctrl+C to terminate both servers.`n"

try {
    Wait-Process -Id $backendJob.Id, $frontendJob.Id
} finally {
    Stop-Process -Id $backendJob.Id -Force -ErrorAction SilentlyContinue
    Stop-Process -Id $frontendJob.Id -Force -ErrorAction SilentlyContinue
}
