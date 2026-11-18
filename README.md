# FAULTTRACE AI: Intelligent Distribution Fault Localization & Advisory Restoration

[![BESCOM Power Hack 2026](https://img.shields.io/badge/BESCOM-Power%20Hack%202026%20Theme%2010-orange.svg)](https://bescom.karnataka.gov.in/)
[![Backend: FastAPI](https://img.shields.io/badge/Backend-FastAPI%200.115-009688.svg)](https://fastapi.tiangolo.com/)
[![Frontend: React 18](https://img.shields.io/badge/Frontend-React%2018%20+%20Vite%205-61DAFB.svg)](https://react.dev/)
[![ML: XGBoost](https://img.shields.io/badge/ML-XGBoost%20+%20Tree%20SHAP-FF6600.svg)](https://xgboost.readthedocs.io/)
[![Graph: NetworkX](https://img.shields.io/badge/Graph-NetworkX%203.4-blue.svg)](https://networkx.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

**FAULTTRACE AI** is an intelligent distribution grid fault localization and advisory restoration decision-support platform engineered for the **Bangalore Electricity Supply Company Limited (BESCOM)** under **Theme 10**.

In modern urban distribution networks like Bengaluru, overhead conductor snaps, transformer overloads, and tree-fall branch faults cause severe cascading outages. Control room engineers are inundated with unstructured tele-reports, delayed 1912 customer complaints, and conflicting breaker trips. 

FAULTTRACE AI bridges the operational gap between SCADA alarms, AMI smart meter pings, customer complaints, and field switching crews by executing a deterministic, multi-stage resilience pipeline:

```
COLLECT ──> CORRELATE ──> PRUNE ──> RANK ──> CALIBRATE ──> RESTORE
```

---

## ⚡ System Architecture

```mermaid
flowchart TD
    subgraph INGESTION ["1. Ingestion & Event Correlation (15-Min Window)"]
        SCADA["SCADA Breaker Trips\n(Sequence of Events)"]
        AMI["AMI Smart Meter Telemetry\n(Voltage Sags / Loss)"]
        CRM["1912 Customer Complaints\n(Spatial Cluster Points)"]
        WX["Open-Meteo Weather\n(Wind Gusts & Rain)"]
        CORR["Rolling 15-Minute\nEvent Correlator"]
        SCADA --> CORR
        AMI --> CORR
        CRM --> CORR
        WX --> CORR
    end

    subgraph GRAPH ["2. Topological Search Space Pruning"]
        DB[(Distribution Grid DB\nSubstations, Feeders, DTs)]
        NX["NetworkX Radial Tree\nGraph Engine"]
        PRUNE["Topology-Consistent\nCandidate Pruning\n(91.56% Pruned)"]
        DB --> NX
        CORR --> PRUNE
        NX --> PRUNE
    end

    subgraph ML ["3. ML Ranking & Calibrated Probabilities"]
        FEAT["27 Multi-Modal Features\n(Topology, Voltage, Complaints, Health)"]
        XGB["XGBoost Ranker\n(Top-1: 62.7% | Top-3: 89.3%)"]
        CALIB["Isotonic Calibration\n(Synthetic Test ECE = 0.0054)"]
        SHAP["Tree SHAP Attribution\n(Feature Contributions)"]
        PRUNE --> FEAT
        FEAT --> XGB
        XGB --> CALIB
        XGB --> SHAP
    end

    subgraph RESTORATION ["4. Advisory Switching & Safety Invariant"]
        PLANNER["Advisory Restoration Planner\n(LOTO Isolation Protocol)"]
        HEADROOM["Donor Feeder Headroom Check\n(Tie Switches TS-F4-F5)"]
        SAFETY["Engineer Mandatory Review\n(Zero Auto-Execution)"]
        CALIB --> PLANNER
        SHAP --> PLANNER
        HEADROOM --> PLANNER
        PLANNER --> SAFETY
    end

    subgraph UI ["5. Control-Room Operations Frontend"]
        REACT["React 18 + Vite + Tailwind"]
        MAP["React-Leaflet GIS Map\n(Synthetic Bengaluru Grid)"]
        DASH["Real-Time Dashboard & KPIs\n(DB Aggregated Metrics)"]
        INCIDENT["Incident Deep Dive\n(SHAP Charts & Switching Steps)"]
        SAFETY --> REACT
        REACT --> MAP
        REACT --> DASH
        REACT --> INCIDENT
    end
```

---

## 🛠️ Prerequisites

- **Python**: `3.11+` (Virtual environment strongly recommended)
- **Node.js**: `v18.0.0+` or `v20.0.0+` (with `npm`)
- **Docker & Docker Compose** *(Optional)*: For running PostgreSQL container; SQLite fallback is fully automatic and built-in.
- **Operating System**: Windows, macOS, or Linux.

---

## ⚙️ Environment Configuration

1. Clone or navigate to the repository root:
   ```bash
   cd FaultTrace
   ```

2. Copy the example environment file:
   ```bash
   # On Windows (PowerShell)
   Copy-Item .env.example .env

   # On Linux / macOS
   cp .env.example .env
   ```

3. Default `.env` values:
   ```ini
   APP_NAME="FAULTTRACE AI"
   APP_VERSION="1.0.0"
   ENVIRONMENT="development"
   DEBUG=True

   # Database (defaults to SQLite fallback if PostgreSQL is not active)
   DATABASE_URL="sqlite:///./faulttrace.db"
   # To use PostgreSQL:
   # DATABASE_URL="postgresql://faulttrace_user:faulttrace_password@localhost:5432/faulttrace"

   # Correlation & Calibration Configuration
   CORRELATION_WINDOW_MINUTES=15
   CALIBRATION_METHOD="isotonic"
   OPEN_METEO_ENABLED=True
   ```

---

## 🗄️ Database Setup

### Option A: PostgreSQL with Docker Compose (Recommended for Production)
Start the PostgreSQL container:
```bash
docker compose up -d
```
Verify the container is healthy:
```bash
docker compose ps
```

### Option B: Automatic SQLite Fallback (Zero Config)
If Docker or PostgreSQL is not installed, FAULTTRACE AI automatically falls back to an embedded SQLite database (`faulttrace.db`) with foreign key constraints enabled. No configuration is necessary.

---

## 📦 Python Virtual Environment & Dependencies

1. Create and activate a Python 3.11 virtual environment:
   ```bash
   # Windows (PowerShell)
   python -m venv backend\.venv
   .\backend\.venv\Scripts\Activate.ps1

   # Linux / macOS
   python3 -m venv backend/.venv
   source backend/.venv/bin/activate
   ```

2. Install dependencies:
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

---

## 🧠 Database Seeding & Model Training

1. **Seed the Synthetic Bengaluru Network**:
   Populates 2 substations (`SS-NORTH-01`, `SS-EAST-02`), 8 feeders (`F1`..`F8`), 140 sections, 48 transformers, 4 critical facilities (Hospital, Water Pump, Oxygen Plant), and tie switches:
   ```bash
   python -m backend.app.database.seed
   ```

2. **Generate Synthetic Scenarios & Train XGBoost Model**:
   Simulates 2,500 scenarios, extracts 27 topology and telemetry features, executes scenario-split partitioning (`GroupShuffleSplit`), trains the XGBoost ranker, fits Isotonic probability calibration, computes test ECE, and exports artifacts to `models/`:
   ```bash
   python -m backend.app.ml_engine.trainer
   ```

---

## 🚀 Running the Application

### 1. Start the Backend API Server
```bash
# From repository root with venv activated:
python -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```
- Interactive Swagger API Docs: [http://localhost:8000/docs](http://localhost:8000/docs)
- System Health Endpoint: [http://localhost:8000/health](http://localhost:8000/health)

### 2. Start the Frontend Control Room
In a separate terminal:
```bash
cd frontend
npm install
npm run dev
```
- Control Room Web Interface: [http://localhost:5173](http://localhost:5173)

---

## 🧪 Running the Test Suites

### Backend Unit & Integration Tests (pytest)
Runs 33 automated tests covering models, graph traversal, XGBoost metrics, SHAP attributions, CSV ingestion, 422 error handling, and API endpoints:
```bash
# Windows
.\backend\.venv\Scripts\python.exe -m pytest backend/tests -v

# Linux / macOS
pytest backend/tests -v
```

### Frontend UI & Client Tests (Vitest)
Runs client-side API error handling and safety advisory banner unit tests:
```bash
cd frontend
npm test -- --run
```

### Frontend Production Build Verification
```bash
cd frontend
npm run build
```

---

## ⚡ One-Click Startup Script

To seed the database, train the ML model, verify tests, and start both servers in a single step:

- **Windows (PowerShell)**:
  ```powershell
  .\run_all.ps1
  ```
- **Windows (Command Prompt / Batch)**:
  ```cmd
  run_all.bat
  ```
- **Linux / macOS (Bash)**:
  ```bash
  chmod +x run_all.sh
  ./run_all.sh
  ```

---

## 🔍 Key Capabilities & Control Room Pages

1. **Dashboard (`/`)**:
   Live KPI cards (Active Incidents, Outage DTs, Affected Consumers, Mean Restoration Time), 7-day outage timeline, feeder health cards, and fault category distributions.
2. **Network Map (`/map`)**:
   GIS visualization (React-Leaflet) of the Bengaluru distribution grid. Real-time section states, transformer pins, tie switches, and candidate highlight boundaries.
3. **Simulation & Ingestion (`/simulate`)**:
   Trigger the pre-monsoon storm Feeder F4 Hero Scenario, run randomized Monte Carlo fault cases, or upload operational CSV telemetry with instant validation feedback.
4. **Incident Deep Dive (`/incidents/:id`)**:
   Candidate ranking table (Score vs. Calibrated Probability), interactive Tree SHAP attribution bar charts, "Why Lower Ranked?" comparative delta analysis, and advisory restoration steps.
5. **Asset Explorer (`/assets`)**:
   Multi-parameter asset health index filtering across transformers, breakers, conductors, and critical facilities.
6. **Restoration Advisory (`/restoration`)**:
   Advisory switching schedules enforcing the mandatory Lock-Out / Tag-Out (LOTO) safety invariant and donor feeder capacity headroom checks.
7. **Model Evaluation (`/model`)**:
   Empirical metrics from held-out test scenarios: Confusion matrix, Top-1 / Top-3 accuracy, ROC-AUC, Precision-Recall curve, and Brier reliability diagram.

---

## 🛠️ Troubleshooting

| Issue | Cause | Solution |
| :--- | :--- | :--- |
| `File ... cannot be loaded because running scripts is disabled` | Windows PowerShell execution policy | Run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` in your PowerShell session. |
| `WinError 10013 / Address already in use: 8000` | Port 8000 occupied by another process | Terminate the process using port 8000: `netstat -ano \| findstr :8000` followed by `taskkill /PID <PID> /F`. |
| `sqlite3.OperationalError: database is locked` | Concurrent SQLite write lock | Stop background runner tasks or verify only one instance of uvicorn is writing to `faulttrace.db`. |
| `Form data requires python-multipart to be installed` | Missing multipart package for CSV uploads | Run `pip install python-multipart>=0.0.34`. |
| `Vite proxy error: ECONNREFUSED 127.0.0.1:8000` | Frontend started before backend server | Ensure the FastAPI backend is running on port 8000 before navigating the frontend UI. |

---

## 📄 Documentation Index

- [Demo Script (5-Minute Walkthrough & Backups)](file:///docs/DEMO_SCRIPT.md)
- [Operational Limitations & Synthetic Assumptions](file:///docs/LIMITATIONS.md)
- [Model Evaluation & Pitch Metric Reconciliation](file:///docs/METRICS.md)
- [Judge Q&A: 12 Technical Defense Questions](file:///docs/JUDGE_QA.md)

---

## 📜 License & Disclaimers

This software is developed for demonstration purposes under **BESCOM Power Hack 2026**.  
**SAFETY NOTICE**: Restoration switching instructions generated by FAULTTRACE AI are strictly **advisory** decision support recommendations. All switching commands require manual operator authorization and mandatory Lock-Out / Tag-Out (LOTO) field verification. Automated tele-control switching is explicitly disabled.