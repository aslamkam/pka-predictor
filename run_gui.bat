@echo off
REM Launch the pKa Predictor GUI in your browser (Windows).
REM Builds the Docker image on first run, then serves the Gradio GUI on :7860.
REM Predictions + extracted UMA embeddings + the uma-s-1p2 download persist in .\cache.
cd /d "%~dp0"
if not exist cache mkdir cache
REM Fetch model binaries (~728 MB) on first run; no-op once present.
call "%~dp0scripts\fetch_assets.bat"
if errorlevel 1 exit /b 1
docker image inspect pkapredict >nul 2>&1
if errorlevel 1 (
  echo >> Building image 'pkapredict' (first run; installs torch+fairchem - several minutes)...
  docker build -t pkapredict .
)
echo >> GUI starting at http://localhost:7860  (Ctrl-C to stop)
start "" http://localhost:7860
docker run --rm -p 7860:7860 -v "%CD%\cache":/cache pkapredict gui
