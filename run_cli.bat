@echo off
REM Run the pKa Predictor CLI natively on Windows (NO Docker required).
REM   run_cli.bat list
REM   run_cli.bat predict --smiles "C1CCCN1" --models uma-invt --temp 298.15
REM   run_cli.bat plot --smiles "C1CCCN1" --model uma-invt --n 10 --step 10 --unit C
cd /d "%~dp0"
if not exist cache mkdir cache

where python >nul 2>&1
if errorlevel 1 (
  echo ERROR: python not found on PATH. Install Python 3.10-3.12 from https://www.python.org/downloads/ >&2
  exit /b 1
)

if not exist .venv\Scripts\python.exe (
  echo Creating virtual environment .venv ...
  python -m venv .venv
  if errorlevel 1 exit /b 1
)
set "PY=.venv\Scripts\python.exe"

if not exist .venv\.deps_ok (
  echo Installing dependencies - first run only ... >&2
  "%PY%" -m pip install --upgrade pip
  "%PY%" -m pip install -r requirements.txt
  if errorlevel 1 exit /b 1
  echo ok> .venv\.deps_ok
)

call "%~dp0scripts\fetch_assets.bat"
if errorlevel 1 exit /b 1

if not defined HF_TOKEN (
  if exist "%~dp0.hf_token" set /p HF_TOKEN=<"%~dp0.hf_token"
)

"%PY%" cli.py %*
