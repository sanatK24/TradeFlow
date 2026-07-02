# TradeFlow - Electronic Trading Simulator Launcher
# Usage: .\run.ps1

Clear-Host
Write-Host "=============================================" -ForegroundColor DarkMagenta
Write-Host "       TradeFlow Trading Desk Launcher      " -ForegroundColor DarkMagenta
Write-Host "=============================================" -ForegroundColor DarkMagenta

# 1. Start backend in a separate window
Write-Host "[1/2] Spinning up FastAPI Backend..." -ForegroundColor Blue
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd backend; .\venv\Scripts\activate; uvicorn app.main:app --reload --port 8000"

# 2. Start frontend in a separate window
Write-Host "[2/2] Launching Vite React Dashboard..." -ForegroundColor Magenta
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd frontend; npm run dev"

Write-Host "---------------------------------------------" -ForegroundColor Gray
Write-Host "TradeFlow simulator launched successfully!" -ForegroundColor Green
Write-Host "- Backend API Docs:  http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host "- Frontend Trading:  http://localhost:5173" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor DarkMagenta
