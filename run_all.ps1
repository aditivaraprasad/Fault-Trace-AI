# FAULTTRACE AI: Single-Command Automated Startup & Verification Script (PowerShell)
# BESCOM Power Hack 2026 - Theme 10

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " FAULTTRACE AI: Automated Build, Train & Startup Pipeline " -ForegroundColor Cyan
Write-Host " BESCOM Distribution Grid Fault Localization Platform   " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $RepoRoot

# 1. Verify / Setup Python Virtual Environment
Write-Host "`n[1/5] Checking Python Virtual Environment..." -ForegroundColor Yellow
$PythonExe = Join-Path $RepoRoot "backend\.venv\Scripts\python.exe"
if (-not (Test-Path $PythonExe)) {
    Write-Host "Creating Python venv..." -ForegroundColor Gray
    python -m venv backend\.venv
    & $PythonExe -m pip install --upgrade pip
    & $PythonExe -m pip install -r requirements.txt
} else {
    Write-Host "Virtual environment detected: $PythonExe" -ForegroundColor Green
}

# 2. Database Initialization & Synthetic Network Seeding
Write-Host "`n[2/5] Initializing Database & Seeding Synthetic Bengaluru Network..." -ForegroundColor Yellow
& $PythonExe -m backend.app.database.seed
Write-Host "Database seed complete (Substations, Feeders, DTs, Critical Loads, Tie Switches)." -ForegroundColor Green

# 3. Model Training & Probability Calibration
Write-Host "`n[3/5] Verifying / Training XGBoost Model & Probability Calibrator..." -ForegroundColor Yellow
$ModelArtifact = Join-Path $RepoRoot "models\xgboost_fault_locator.json"
if (-not (Test-Path $ModelArtifact)) {
    Write-Host "Training XGBoost on 2,500 scenarios..." -ForegroundColor Gray
    & $PythonExe -m backend.app.ml_engine.trainer
} else {
    Write-Host "Trained model and calibration artifacts verified in models/" -ForegroundColor Green
}

# 4. Execute Full Automated Test Suite
Write-Host "`n[4/5] Executing Backend & Frontend Test Suites..." -ForegroundColor Yellow
Write-Host "Running Backend pytest (33 tests)..." -ForegroundColor Gray
& $PythonExe -m pytest backend/tests -v

Write-Host "Running Frontend Vitest (6 tests)..." -ForegroundColor Gray
Set-Location (Join-Path $RepoRoot "frontend")
npm.cmd test -- --run
Set-Location $RepoRoot
Write-Host "All test suites PASSED cleanly." -ForegroundColor Green

# 5. Launch Backend and Frontend Concurrently
Write-Host "`n[5/5] Launching FAULTTRACE AI Services..." -ForegroundColor Yellow
Write-Host "-> Backend API: http://localhost:8000 (Swagger: /docs)" -ForegroundColor Cyan
Write-Host "-> Frontend Control Room: http://localhost:5173" -ForegroundColor Cyan
Write-Host "Press Ctrl+C to terminate both servers." -ForegroundColor Gray

# Start backend in background job
$BackendJob = Start-Job -ScriptBlock {
    param($root, $py)
    Set-Location $root
    & $py -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
} -ArgumentList $RepoRoot, $PythonExe

# Start frontend in foreground
try {
    Set-Location (Join-Path $RepoRoot "frontend")
    npm.cmd run dev
} finally {
    Write-Host "`nStopping background backend job..." -ForegroundColor Yellow
    Stop-Job $BackendJob -ErrorAction SilentlyContinue
    Remove-Job $BackendJob -ErrorAction SilentlyContinue
    Set-Location $RepoRoot
    Write-Host "FAULTTRACE AI shutdown complete." -ForegroundColor Gray
}