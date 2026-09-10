@echo off
REM Launch the pKa Predictor GUI natively on Windows (NO Docker required).
REM First run: creates .venv, pip-installs requirements.txt, fetches the model
REM asset bundle (one-time). Later runs start in seconds.
REM Predictions + extracted UMA embeddings + the uma-s-1p2 download persist in .\cache.
cd /d "%~dp0"
if not exist cache mkdir cache

REM 1) Python (3.10-3.12 recommended)
where python >nul 2>&1
if errorlevel 1 (
  echo ERROR: python not found on PATH. Install Python 3.10-3.12 from https://www.python.org/downloads/ >&2
  echo        ^(tick "Add python.exe to PATH" during install^), then re-run this file. >&2
  exit /b 1
)

REM 2) Virtual environment
if not exist .venv\Scripts\python.exe (
  echo Creating virtual environment .venv ...
  python -m venv .venv
  if errorlevel 1 exit /b 1
)
set "PY=.venv\Scripts\python.exe"

REM 3) Dependencies (first run only; several minutes - torch + fairchem are large)
if not exist .venv\.deps_ok (
  echo Installing dependencies - first run only ...
  "%PY%" -m pip install --upgrade pip
  "%PY%" -m pip install -r requirements.txt
  if errorlevel 1 (
    echo ERROR: dependency install failed. See INSTALL.md ^(Troubleshooting^). >&2
    exit /b 1
  )
  echo ok> .venv\.deps_ok
)

REM 4) Model binaries on first run; no-op once present.
call "%~dp0scripts\fetch_assets.bat"
if errorlevel 1 exit /b 1

REM 5) HuggingFace token (for the gated uma-s-1p2 model; standard models work without it)
if not defined HF_TOKEN (
  if exist "%~dp0.hf_token" set /p HF_TOKEN=<"%~dp0.hf_token"
)
if not defined HF_TOKEN (
  echo No HF_TOKEN found: UMA models will fail to download uma-s-1p2. See INSTALL.md.
)

echo GUI starting at http://localhost:7860  - Ctrl-C to stop
start "" http://localhost:7860
"%PY%" app.py
