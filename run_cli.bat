@echo off
REM Run the pKa Predictor CLI inside Docker (Windows).
REM   run_cli.bat list
REM   run_cli.bat predict --smiles "C1CCCN1" --models uma-invt --temp 298.15
REM   run_cli.bat plot --smiles "C1CCCN1" --model uma-invt --n 10 --step 10 --unit C
cd /d "%~dp0"
if not exist cache mkdir cache
REM Fetch model binaries (~728 MB) on first run; no-op once present.
call "%~dp0scripts\fetch_assets.bat"
if errorlevel 1 exit /b 1
docker image inspect pkapredict >nul 2>&1
if errorlevel 1 (
  echo >> Building image 'pkapredict' (first run)... >&2
  docker build -t pkapredict . >&2
)
docker run --rm -i -v "%CD%\cache":/cache pkapredict %*
