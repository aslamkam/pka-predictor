@echo off
REM Resolve the HuggingFace token and write it to a --env-file for `docker run`.
REM
REM Source priority:
REM   1. %HF_TOKEN% environment variable (if set)
REM   2. .hf_token file next to this script's parent (the pka_app/ dir)
REM
REM Writes "HF_TOKEN=<value>" to a temp file and prints its path to stdout
REM (captured by the caller via for /f). The temp file is in the user's %TEMP%.
REM If no token is found, prints an empty line (caller then omits --env-file).
REM
REM The .hf_token file is gitignored — put your token there as a single line.
setlocal enabledelayedexpansion
set "APP_DIR=%~dp0.."
set "TOKEN="

if defined HF_TOKEN (
  set "TOKEN=!HF_TOKEN!"
) else if exist "%APP_DIR%\.hf_token" (
  set /p TOKEN=<"%APP_DIR%\.hf_token"
)

if "!TOKEN!"=="" (
  echo(
  exit /b 0
)

set "ENVFILE=%TEMP%\pka_hf_env.%RANDOM%.txt"
echo HF_TOKEN=!TOKEN!> "%ENVFILE%"
echo %ENVFILE%
endlocal
exit /b 0
