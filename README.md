# EATCalc

EATCalc computes epicardial adipose tissue (EAT) volume from CT scans. The backend uses FastAPI and TotalSegmentator for pericardium segmentation; the frontend is a Vite + React app.

## Prerequisites
- Python 3.9+ (conda or venv)
- Node.js 18+ and npm
- TotalSegmentator installed separately: https://github.com/wasserth/TotalSegmentator
  - Make sure the `TotalSegmentator` CLI is on your PATH: `TotalSegmentator --help`

## Setup (recommended order)
1. Create/activate a Python environment (conda or venv).
2. Install Python deps:

```sh
pip install -r backend/requirements.txt
```

3. Install TotalSegmentator (see link above).
4. Install frontend deps:

```sh
npm install
```

## Run locally
Option A (Windows):

```sh
start_dev.bat
```

Option B (manual, two terminals):

```sh
# Terminal 1
uvicorn backend.server:app --reload --port 8000

# Terminal 2
npm run dev -- --host 127.0.0.1 --port 8080
```

Then open http://127.0.0.1:8080.

## Notes
- Backend outputs default to `backend/output` (override via the `output_path` form field).
- The API runs on http://127.0.0.1:8000.
