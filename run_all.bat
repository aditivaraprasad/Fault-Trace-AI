@echo off
REM FAULTTRACE AI: Single-Command Automated Startup & Verification Script (Windows CMD)
REM BESCOM Power Hack 2026 - Theme 10

echo ==========================================================
echo  FAULTTRACE AI: Automated Build, Train ^& Startup Pipeline
echo  BESCOM Distribution Grid Fault Localization Platform
echo ==========================================================

cd /d "%~dp0"

REM 1. Check Python Venv
echo.
echo [1/5] Checking Python Virtual Environment...
set PYTHON_EXE=backend\.venv\Scripts\python.exe
if not exist "%PYTHON_EXE%" (
    echo Creating Python venv...
    python -m venv backend\.venv
    %PYTHON_EXE% -m pip install --upgrade pip
    %PYTHON_EXE% -m pip install -r requirements.txt
) else (
    echo Python environment ready: %PYTHON_EXE%
)

REM 2. Seed Database
echo.
echo [2/5] Initializing Database ^& Seeding Synthetic Network...
"%PYTHON_EXE%" -m backend.app.database.seed
if errorlevel 1 exit /b 1

REM 3. Train Model
echo.
echo [3/5] Verifying / Training XGBoost Model...
if not exist "models\xgboost_fault_locator.json" (
    "%PYTHON_EXE%" -m backend.app.ml_engine.trainer
) else (
    echo Model artifacts exist in models\
)

REM 4. Run Tests
echo.
echo [4/5] Running Verification Tests...
"%PYTHON_EXE%" -m pytest backend/tests -v
if errorlevel 1 exit /b 1

cd frontend
call npm.cmd test -- --run
if errorlevel 1 exit /b 1
cd ..

REM 5. Run Backend & Frontend
echo.
echo [5/5] Starting Backend and Frontend Servers...
echo -> Backend: http://localhost:8000
echo -> Frontend: http://localhost:5173
start "FAULTTRACE Backend" "%PYTHON_EXE%" -m uvicorn backend.app.main:app --reload --port 8000
cd frontend
call npm.cmd run dev
