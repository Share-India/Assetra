# Deployment & Operations Guide

## ASSETRA - Fixed Asset Replacement Value Calculator

---

### Table of Contents
1. [Overview & Architecture](#1-overview--architecture)
2. [Project Layout](#2-project-layout)
3. [Prerequisites](#3-prerequisites)
4. [Environment Configuration (.env)](#4-environment-configuration-env)
5. [Dependency Installation (Pinned Requirements)](#5-dependency-installation-pinned-requirements)
6. [Single-Worker Execution Policy](#6-single-worker-execution-policy)
7. [Starting the Application](#7-starting-the-application)
8. [Long Jobs & Background Worker Architecture](#8-long-jobs--background-worker-architecture)
9. [Health Monitoring & Logs](#9-health-monitoring--logs)
10. [Automated Housekeeping & Cleanup](#10-automated-housekeeping--cleanup)
11. [Step-by-Step Restart Instructions](#11-step-by-step-restart-instructions)

---

### 1. Overview & Architecture

The **ASSETRA Replacement Value Calculator** calculates the current estimated replacement values of fixed assets using historical Wholesale Price Index (WPI) time series data from 1954 to 2025.

- **Backend:** FastAPI (Python), Pandas, Openpyxl, Google GenAI SDK.
- **Frontend:** React 18, Vite, Lucide Icons.
- **Long Job Processing:** Background execution thread with polling progress endpoint (`/calculate-job/{job_id}`).
- **Data Persistence:** In-memory caching with filesystem JSON caches (`category_cache.json`, `alias_cache.json`).

---

### 2. Project Layout

The repository is structured into four primary modules:

```text
FAR/
│
├── backend/                  # FastAPI backend server
│   ├── data/                 # Master datasets (WPI series, category rules, ASSET_GROUPS)
│   ├── downloads/            # Generated Excel reports (cleaned every 7 days)
│   ├── calculator.py         # Deterministic WPI replacement value calculation engine
│   ├── column_mapper.py      # Automated column header detection & alias resolver
│   ├── main.py               # FastAPI application, async job queue, and endpoints
│   ├── requirements.txt      # Pinned Python package dependencies
│   ├── app.log               # Application logs (API key automatically redacted)
│   └── .env.example          # Environment template for backend
│
├── frontend/                 # React + Vite user interface
│   ├── src/                  # React source components
│   │   ├── App.jsx           # Full responsive UI (375px to desktop) with progress modal
│   │   └── main.jsx          # React DOM entrypoint
│   ├── package.json          # Node dependencies and scripts
│   ├── vite.config.js        # Vite build configuration
│   └── .env.example          # Environment template for frontend
│
├── deploy/                   # Startup & deployment automation scripts
│   ├── start_project.bat     # Consolidated project starter (health-check guarded)
│   ├── start_backend.bat     # Backend launcher (--workers 1)
│   └── start_frontend.bat    # Frontend Vite dev server launcher
│
├── docs/                     # Documentation
│   └── DEPLOY.md             # This deployment and operations guide
│
├── .gitignore                # Git ignore rules (.env, downloads, __pycache__, node_modules)
└── start_project.bat         # Root convenience launcher
```

---

### 3. Prerequisites

Ensure the deployment host has the following runtimes installed:

| Component | Minimum Version | Recommended Version |
| :--- | :--- | :--- |
| **Operating System** | Windows 10 / Server 2019+ | Windows 11 / Server 2022 |
| **Python** | 3.9+ | 3.11 / 3.12 |
| **Node.js** | 18.0.0+ | 20.x LTS |
| **npm** | 9.0.0+ | 10.x |

---

### 4. Environment Configuration (.env)

#### A. Backend Configuration (`backend/.env`)

Copy `backend/.env.example` to `backend/.env`:

```bash
cd backend
copy .env.example .env
```

Configure the environment variables:

```ini
# Gemini API Configuration (Google AI Studio)
# Used strictly for industry suggestion assistance
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash

# Security & CORS Settings
# Comma-separated list of allowed browser origins
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

# Server & Upload Limits
PORT=8000
MAX_UPLOAD_SIZE_MB=100

# Logging
LOG_LEVEL=INFO
```

> [!IMPORTANT]
> **API Key Security**: The application implements a `SafeLogFilter` logging filter. The Gemini API key is intercepted and masked (`[REDACTED_API_KEY]`) before any log record is written to `app.log` or printed to console.

#### B. Frontend Configuration (`frontend/.env`)

Copy `frontend/.env.example` to `frontend/.env`:

```bash
cd frontend
copy .env.example .env
```

Content:
```ini
# Base URL for the FastAPI backend service
VITE_API_BASE_URL=http://127.0.0.1:8000
```

---

### 5. Dependency Installation (Pinned Requirements)

#### Backend Virtual Environment Setup

Always use the pinned `requirements.txt` to ensure reproducible builds:

```cmd
cd backend
python -m venv venv2
call venv2\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Pinned dependencies include:
- `fastapi==0.141.1`
- `uvicorn==0.52.3`
- `python-dotenv==1.2.3`
- `google-genai==2.18.1`
- `pandas==3.0.5`
- `numpy==2.5.2`
- `openpyxl==3.1.5`
- `python-multipart==0.0.32`
- `pyxlsb==1.0.10`
- `requests==2.34.2`
- `pydantic==2.13.4`

#### Frontend Setup

```cmd
cd frontend
npm install
```

---

### 6. Single-Worker Execution Policy

> [!CAUTION]
> **Run Exactly One Worker**: Uvicorn must be launched with `--workers 1` (or without multi-process clustering).
> 
> **Why?**
> 1. In-memory asynchronous calculation job tracking (`JOBS` dictionary) resides within a single process.
> 2. Cache files (`category_cache.json` and `alias_cache.json`) avoid concurrency lock conflicts.
> 3. Master WPI reference datasets are loaded into memory once during process startup.

---

### 7. Starting the Application

#### Option A: Quick Start (Recommended)
Run the automated launcher from the project root:
```cmd
start_project.bat
```
This launcher:
1. Starts the backend in a dedicated window with `--workers 1`.
2. Probes `http://127.0.0.1:8000/health` until the backend is healthy.
3. Automatically launches the Vite frontend server on `http://localhost:3000`.

#### Option B: Manual Service Startup

**Terminal 1 — Backend:**
```cmd
cd backend
.\venv2\Scripts\activate
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --workers 1
```

**Terminal 2 — Frontend:**
```cmd
cd frontend
npm run dev
```

---

### 8. Long Jobs & Background Worker Architecture

Large Fixed Asset Registers (e.g., 15,000 to 50,000+ rows) can take 20–60 seconds to process through multi-stage historical WPI linking. To prevent HTTP gateway timeouts:

1. **Submission:** `POST /calculate-job` streams the file to temporary disk storage, validates `MAX_UPLOAD_SIZE_MB`, and returns a unique `job_id`.
2. **Background Processing:** A background worker thread executes `process_file(...)` with real-time progress callbacks:
   - 5%: Sheet analysis & header detection
   - 15%: Column mapping resolution
   - 25%: Asset extraction
   - 40%–90%: Calculation loop (updates every 500 rows)
   - 92%: Result compilation
   - 100%: Excel output generation & metrics calculation
3. **UI Polling:** Frontend polls `GET /calculate-job/{job_id}` every 600ms, displaying a progress modal with percentage and stage status.
4. **Completion:** When status reaches `completed`, the frontend seamlessly displays the Review/Results dashboard.

---

### 9. Health Monitoring & Logs

#### Health Check Endpoint
Query the server health status:
```cmd
curl http://127.0.0.1:8000/health
```

Sample JSON response:
```json
{
  "status": "ok",
  "max_upload_size_mb": 100,
  "active_jobs": 0,
  "wpi_data": "loaded",
  "asset_mapping": "loaded",
  "commodity_master": "loaded",
  "series_master": "loaded",
  "industry_mapping": "loaded"
}
```

#### Log Inspection
Logs are recorded both in the console and in `backend/app.log`:
```cmd
powershell Get-Content -Tail 50 -Wait backend\app.log
```
All API keys are verified scrubbed before being written.

---

### 10. Automated Housekeeping & Cleanup

- **Downloads Retention:** Output spreadsheets in `backend/downloads/` older than **7 days** are automatically pruned on server startup and upon job completion (`cleanup_old_downloads(days=7)`).
- **Temporary Uploads:** In-flight temporary files (`temp_*`) are cleaned up immediately in `finally` blocks.

---

### 11. Step-by-Step Restart Instructions

To gracefully restart the services (e.g., after configuration or dataset updates):

1. **Stop Frontend:** In the frontend console window, press `Ctrl + C` and type `Y`.
2. **Stop Backend:** In the backend console window, press `Ctrl + C`. If running in background, terminate the process on port 8000:
   ```cmd
   powershell "Get-Process -Id (Get-NetTCPConnection -LocalPort 8000).OwningProcess | Stop-Process -Force"
   ```
3. **Verify Port Release:** Ensure port 8000 is free:
   ```cmd
   netstat -ano | findstr :8000
   ```
4. **Restart Services:**
   Run `deploy\start_project.bat` or run `start_project.bat` from root.
5. **Verify Health:**
   Check `http://127.0.0.1:8000/health` returns `status: "ok"`.
