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

## Measurement definition and reproducibility
EATCalc-classic 1.0.0 reports intrapericardial fat (TotalSegmentator `trunk_cavities` pericardium, −190 to −30 HU) as a CT proxy for EAT. See [docs/MEASUREMENT_DEFINITION.md](docs/MEASUREMENT_DEFINITION.md).

- Every analysis writes `eat_provenance.json` (method version, HU window, TotalSegmentator version, git commit, input CT hash). `GET /api/version` returns the current setup.
- Record the environment after installing or upgrading: `scripts\freeze_env.bat`.
- Tests: `pip install -r backend/requirements-dev.txt` then `python -m pytest tests -q`.
- After upgrading TotalSegmentator, check that outputs haven't drifted: `python -m scripts.regression_check compare --ct-dir <reference CTs> --baseline eval/baseline` (record the baseline once with `record`).
