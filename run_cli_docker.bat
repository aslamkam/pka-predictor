@echo off
REM Run the pKa Predictor CLI inside Docker (Windows).
REM NOTE: the default run_cli.bat is the NATIVE (no-Docker) install — use this
REM file only if you prefer the Docker setup (see INSTALL.md).
REM   run_cli_docker.bat list
REM   run_cli_docker.bat predict --smiles "C1CCCN1" --models uma-invt --temp 298.15
REM   run_cli_docker.bat plot --smiles "C1CCCN1" --model uma-invt --n 10 --step 10 --unit C
cd /d "%~dp0"
if not exist cache mkdir cache
REM Fetch model binaries on first run; no-op once present.
call "%~dp0scripts\fetch_assets.bat"
if errorlevel 1 exit /b 1
docker image inspect pkapredict >nul 2>&1
if errorlevel 1 (
  echo Building image 'pkapredict' - first run... >&2
  docker build -t pkapredict . >&2
)
REM Resolve HuggingFace token (for the gated uma-s-1p2 model) into a --env-file.
set "HF_ENV="
REM usebackq + backticks handles the quoted script path (single-quote form breaks CMD).
for /f "usebackq delims=" %%P in (`""%~dp0scripts\hf_env_file.bat""`) do set "HF_ENV=%%P"
if defined HF_ENV (
  docker run --rm -i --env-file "%HF_ENV%" -v "%CD%\cache":/cache pkapredict %*
  del /q "%HF_ENV%" >nul 2>&1
) else (
  docker run --rm -i -v "%CD%\cache":/cache pkapredict %*
)
