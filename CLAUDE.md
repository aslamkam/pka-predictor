# CLAUDE.md — agent setup instructions for the pKa Predictor app

This file is written for an AI coding agent (e.g. Claude Code) asked by the
user to "set up and run the pKa Predictor". Follow it top to bottom. The app
installs **natively (no Docker)** on Windows, macOS, and Linux. Docker is an
optional alternative (see the `*_docker.*` launchers and `Dockerfile`).

## What this app is

A Gradio GUI + CLI that predicts pKa from a SMILES string, shipping:
- **30 standard ML models** — ChEMBL 12C/10C amine sets × {Morgan fingerprints,
  Joback-Reid groups, Maginn sigma profile} × {MLP, RF, SVR, XGBoost, CNN}.
  Benson-Groups models were dropped (their RMG feature generator only runs in a
  Linux Docker container); Orca-Sigma is excluded by design.
- **4 UMA models** — the production **v15.1** FairChem `uma-s-1p2` Basicity pKa
  model (pooled relaxed-MLP route; CCUS MAE 0.272), one per temperature head:
  `uma-none`, `uma-linear`, `uma-invt` (preferred), `uma-invtlnt`. These need a
  HuggingFace token for the gated `facebook/UMA` checkpoint (~1 GB, downloaded
  on first UMA prediction).

## Setup steps (native install)

1. **Python**: need Python 3.10–3.12 on PATH (`python --version`).
   - Windows: if missing, install from https://www.python.org/downloads/ (tell
     the user to tick "Add python.exe to PATH"), or `winget install Python.Python.3.12`.
2. **Create the venv and install deps** (from the repo root, the dir containing
   this file):
   - Windows (CMD/PowerShell):
     ```
     python -m venv .venv
     .venv\Scripts\python -m pip install --upgrade pip
     .venv\Scripts\python -m pip install -r requirements.txt
     ```
   - macOS/Linux:
     ```
     python3 -m venv .venv
     .venv/bin/python -m pip install --upgrade pip
     .venv/bin/python -m pip install -r requirements.txt
     ```
   - `torch` from PyPI is fine (CPU is enough; GPU optional). On Windows the
     PyPI torch wheel is large (~2 GB); for a smaller CPU-only install use
     `--index-url https://download.pytorch.org/whl/cpu` for torch first, then
     the rest of requirements.txt.
   - If `fairchem-core` build/install fails, retry with
     `DISABLE_CUDA_EXTENSION=1` set in the environment.
3. **Fetch the model assets** (one-time download, several hundred MB):
   - Windows: `scripts\fetch_assets.bat`  (needs curl.exe + tar.exe, built into
     Windows 10 1803+)
   - macOS/Linux: `./scripts/fetch_assets.sh`
   This populates `models/` (standard artifacts) and `repo/` (UMA checkpoints +
   ChEMBL CSVs) from the GitHub Release. Both are gitignored.
4. **HuggingFace token (only needed for the UMA models)**: the user must create
   a free HF account, request access at https://huggingface.co/facebook/UMA
   (usually instant), create a READ token at
   https://huggingface.co/settings/tokens, and save it as a one-line file named
   `.hf_token` in this directory (gitignored) — or set the `HF_TOKEN` env var.
   Do NOT commit or print the token. Standard models work without it.
5. **Smoke test**:
   ```
   .venv/bin/python cli.py list                                   # 30 std + 4 UMA entries
   .venv/bin/python cli.py predict --smiles "C1CCCN1" --models std-12C-Morgan-Fingerprints-RF
   ```
   (Windows: `.venv\Scripts\python cli.py ...`)
   A UMA smoke test (`--models uma-invt`) only works once a valid HF token is
   in place; the first UMA prediction per molecule takes ~10–60 s on CPU
   (embedding extraction), then results are cached under `cache/`.
6. **Run the GUI**: double-click `run_gui.bat` (Windows) or `./run_gui.sh`
   (macOS/Linux) — or directly: `.venv/bin/python app.py`, then open
   http://localhost:7860. The launchers redo steps 2–4 automatically, so after
   the agent has done them once, the user can just double-click.

## Day-to-day usage (tell the user)

- GUI: enter a SMILES (e.g. pyrrolidine `C1CCCN1`, piperazine `C1CNCCN1`),
  pick models, set temperature, click **Predict**. The lower panel makes
  pKa-vs-T and van't Hoff plots for a chosen UMA head.
- CLI: `run_cli.bat list` / `run_cli.bat predict --smiles "..." --models uma-invt`
  (macOS/Linux: `./run_cli.sh ...`).
- `cache/` holds predictions, extracted embeddings, and the uma-s-1p2 download —
  keep it; deleting it just forces re-downloads.

## Notes for the agent

- `requirements.txt` is the single source of runtime deps. There is no test
  suite; the smoke test in step 5 is the verification.
- `train_standard_models.py` regenerates the standard artifacts (needs the
  ChEMBL CSVs, already in `repo/Features/` after step 3). Not part of setup.
- Do not commit `.hf_token`, `.venv/`, `models/`, `repo/`, or `cache/`
  (all gitignored).
- Docker alternative: `run_gui_docker.bat` / `run_gui_docker.sh` build the
  `pkapredict` image and run the same app in a container.
