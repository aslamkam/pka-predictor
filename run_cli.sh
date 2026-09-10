#!/usr/bin/env bash
# Run the pKa Predictor CLI natively (NO Docker) on Linux/macOS.
#   ./run_cli.sh list
#   ./run_cli.sh predict --smiles "C1CCCN1" --models uma-invt,std-12C-Morgan-Fingerprints-RF --temp 298.15
#   ./run_cli.sh plot --smiles "C1CCCN1" --model uma-invt --n 10 --step 10 --unit C
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p cache

PY=python3
command -v "$PY" >/dev/null 2>&1 || { echo "ERROR: python3 not found (install Python 3.10-3.12)." >&2; exit 1; }

if [ ! -x .venv/bin/python ]; then
  echo ">> Creating virtual environment .venv ..."
  "$PY" -m venv .venv
fi
PY=.venv/bin/python
if [ ! -f .venv/.deps_ok ]; then
  echo ">> Installing dependencies (first run only) ..." >&2
  "$PY" -m pip install --upgrade pip
  "$PY" -m pip install -r requirements.txt
  touch .venv/.deps_ok
fi

./scripts/fetch_assets.sh

if [ -z "${HF_TOKEN:-}" ] && [ -f .hf_token ]; then
  HF_TOKEN="$(head -n 1 .hf_token | tr -d '[:space:]')"
  export HF_TOKEN
fi

exec "$PY" cli.py "$@"
