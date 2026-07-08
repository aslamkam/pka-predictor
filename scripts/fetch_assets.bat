@echo off
REM Download + extract the pKa app's model binaries (models\ + repo\) on first run.
REM
REM The trained artifacts + UMA checkpoints + ChEMBL CSVs (~728 MB) ship as a
REM GitHub Release asset (pka_app_assets.tar.gz), fetched once. Idempotent: exits
REM 0 if the sentinel model already exists.
REM
REM Override the source with the PKA_ASSETS_URL env var (directory holding the
REM tarball) — useful for mirrors or a draft release.
REM
REM Requires curl.exe + tar.exe, both built into Windows 10 1803+.
setlocal

set "APP_DIR=%~dp0.."
set "SENTINEL=%APP_DIR%\models\standard\12C\Morgan-Fingerprints_RF\model.joblib"

if exist "%SENTINEL%" exit /b 0

if "%PKA_ASSETS_URL%"=="" (
  set "URL=https://github.com/aslamkam/jules_experiment/releases/download/v1.0-models/pka_app_assets.tar.gz"
) else (
  set "URL=%PKA_ASSETS_URL%/pka_app_assets.tar.gz"
)

echo >> First run: fetching model assets (~728 MB download, one-time)...
echo >>   from %URL%

where curl.exe >nul 2>&1
if errorlevel 1 (
  echo ERROR: curl.exe not found. Install it ^(Windows 10 1803+ ships it^) or use Git Bash with run_gui.sh. >&2
  exit /b 1
)
where tar.exe >nul 2>&1
if errorlevel 1 (
  echo ERROR: tar.exe not found. Install it ^(Windows 10 1803+ ships it^) or use Git Bash with run_gui.sh. >&2
  exit /b 1
)

set "TMPFILE=%TEMP%\pka_assets.tar.gz"

REM -fL: fail on HTTP errors, follow redirects (release assets redirect to a CDN).
curl.exe -fL -o "%TMPFILE%" "%URL%"
if errorlevel 1 (
  echo ERROR: download failed. The asset may not be published yet, or the URL is wrong: >&2
  echo        %URL% >&2
  exit /b 1
)

echo >> Extracting models\ + repo\ into %APP_DIR% ...
REM The tarball contains top-level models\ and repo\ trees; extract in place.
tar.exe -xzf "%TMPFILE%" -C "%APP_DIR%"
if errorlevel 1 (
  echo ERROR: extraction failed. >&2
  del /q "%TMPFILE%" >nul 2>&1
  exit /b 1
)
del /q "%TMPFILE%" >nul 2>&1

if not exist "%SENTINEL%" (
  echo ERROR: extraction finished but sentinel %SENTINEL% is still missing. >&2
  exit /b 1
)
echo >> Assets ready.
endlocal
exit /b 0
