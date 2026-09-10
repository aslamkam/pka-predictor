#!/usr/bin/env bash
# Launch the pKa Predictor GUI natively (NO Docker) on Linux/macOS.
# First run: creates .venv, pip-installs requirements.txt, fetches the model
# asset bundle (one-time). Later runs start in seconds.
# Predictions + extracted UMA embeddings + the uma-s-1p2 download persist in ./cache.
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p cache

PY=python3
command -v "$PY" >/dev/null 2>&1 || { echo "ERROR: python3 not found (install Python 3.10-3.12)." >&2; exit 1; }

# Virtual environment + dependencies (first run only).
if [ ! -x .venv/bin/python ]; then
  echo ">> Creating virtual environment .venv ..."
  "$PY" -m venv .venv
fi
PY=.venv/bin/python
if [ ! -f .venv/.deps_ok ]; then
  echo ">> Installing dependencies (first run only; torch + fairchem are large) ..."
  "$PY" -m pip install --upgrade pip
  "$PY" -m pip install -r requirements.txt
  touch .venv/.deps_ok
fi

# Model binaries on first run; no-op once present.
./scripts/fetch_assets.sh

# HuggingFace token (for the gated uma-s-1p2 model; standard models work without it).
if [ -z "${HF_TOKEN:-}" ] && [ -f .hf_token ]; then
  HF_TOKEN="$(head -n 1 .hf_token | tr -d '[:space:]')"
  export HF_TOKEN
fi
if [ -z "${HF_TOKEN:-}" ]; then
  echo ">> No HF_TOKEN found: UMA models will fail to download uma-s-1p2. See INSTALL.md." >&2
fi

echo ">> GUI starting at http://localhost:7860  (Ctrl-C to stop)"
( sleep 3; ( xdg-open http://localhost:7860 2>/dev/null || open http://localhost:7860 2>/dev/null ) || true ) &
exec "$PY" app.py
