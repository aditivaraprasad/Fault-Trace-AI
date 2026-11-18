#!/usr/bin/env bash
# FAULTTRACE AI: Single-Command Automated Startup & Verification Script (Linux/macOS)
# BESCOM Power Hack 2026 - Theme 10

set -e
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_ROOT"

echo "=========================================================="
echo " FAULTTRACE AI: Automated Build, Train & Startup Pipeline "
echo " BESCOM Distribution Grid Fault Localization Platform   "
echo "=========================================================="

# 1. Virtual Environment
echo -e "\n[1/5] Checking Python Virtual Environment..."
PYTHON_BIN="backend/.venv/bin/python"
if [ ! -f "$PYTHON_BIN" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv backend/.venv
    $PYTHON_BIN -m pip install --upgrade pip
    $PYTHON_BIN -m pip install -r requirements.txt
else
    echo "Python environment detected: $PYTHON_BIN"
fi

# 2. Database Seeding
echo -e "\n[2/5] Initializing Database & Seeding Synthetic Network..."
$PYTHON_BIN -m backend.app.database.seed

# 3. Model Training
echo -e "\n[3/5] Verifying / Training XGBoost Model..."
if [ ! -f "models/xgboost_fault_locator.json" ]; then
    $PYTHON_BIN -m backend.app.ml_engine.trainer
else
    echo "Model artifacts exist in models/"
fi

# 4. Tests
echo -e "\n[4/5] Running Backend & Frontend Test Suites..."
$PYTHON_BIN -m pytest backend/tests -v
(cd frontend && npm test -- --run)

# 5. Launch Services
echo -e "\n[5/5] Launching FAULTTRACE AI Services..."
echo "-> Backend API: http://localhost:8000"
echo "-> Frontend Control Room: http://localhost:5173"

$PYTHON_BIN -m uvicorn backend.app.main:app --reload --port 8000 &
BACKEND_PID=$!

trap "echo 'Shutting down backend...'; kill $BACKEND_PID" EXIT INT TERM

cd frontend && npm run dev
