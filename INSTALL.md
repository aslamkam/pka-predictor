# pKa Predictor — Setup Guide

This guide installs the app from scratch. **The recommended way is to let
[Claude Code](https://claude.com/claude-code) (an AI coding agent) do the setup
for you** — the repo ships with a `CLAUDE.md` file that tells it exactly what
to do. No Docker is required.

> **What you'll get:** a browser interface at <http://localhost:7860> where you
> type a molecule (as a SMILES string) and get predicted pKa values from 30
> standard ML models and 4 FairChem **UMA v15.1** models, plus
> temperature-sweep plots.

---

## Prerequisites

- A computer running **Windows 10/11**, **macOS**, or **Linux**.
- **Python 3.10–3.12** (the setup agent can install it for you on Windows via
  `winget`, or you can get it from <https://www.python.org/downloads/> — on
  Windows, tick **"Add python.exe to PATH"** during install).
- ~**6 GB free disk space** (Python environment + model bundle + the UMA
  checkpoint).
- An internet connection (only needed for setup and the first UMA prediction).

---

## Step 1 — Get the app

You need **Git** (<https://git-scm.com/downloads>; on Windows accept the
defaults). Open a terminal (Command Prompt, PowerShell, or Terminal) and run:

```
git clone https://github.com/aslamkam/pka-predictor.git
cd pka-predictor
```

The large model files are **not** in git — they download automatically during
setup (Step 3).

---

## Step 2 — Let Claude Code do the setup (recommended)

1. Install Claude Code if you don't have it:
   <https://claude.com/claude-code> (one-line installer for Windows/macOS/Linux;
   requires a Claude account).
2. From the `pka-predictor` folder, start it:
   ```
   claude
   ```
3. Tell it:

   > **"Read CLAUDE.md and set up this app natively (no Docker), then run the
   > smoke test."**

   It will create the Python virtual environment, install the dependencies,
   download the model bundle, and verify everything works. First-time setup
   takes ~15–40 minutes (mostly downloads: PyTorch and the model bundle are
   large).

4. Afterwards, starting the app is just: double-click **`run_gui.bat`**
   (Windows) or run **`./run_gui.sh`** (macOS/Linux). Your browser opens at
   <http://localhost:7860>.

> **Prefer to do it by hand?** See *Manual install* below.
> **Prefer Docker?** See *Docker alternative* below.

---

## Step 3 — HuggingFace access (required for the UMA models only)

The UMA models use a gated model checkpoint (`uma-s-1p2`) hosted on
HuggingFace. **The 30 standard ML models need none of this and work
immediately.** You can do this step while Claude Code runs the setup — tell it
your token is coming.

1. **Create a free HuggingFace account:** <https://huggingface.co/join>
2. **Request access to the model:** go to
   <https://huggingface.co/facebook/UMA> and click **"Acknowledge license"**.
   Approval is usually **instant**.
3. **Create an access token:** <https://huggingface.co/settings/tokens> →
   **"New token"** → type **"Read"** → copy the token (starts with `hf_...`).
4. **Save it** as a plain-text file named exactly **`.hf_token`** (leading dot)
   in the `pka-predictor` folder — the token as the only contents, one line.

   **On Windows:** open Notepad, paste the token, **File → Save As**, filename
   `.hf_token`, **Save as type: "All Files (*.*)"** (otherwise Notepad adds
   `.txt`).

   Or just ask Claude Code: *"save this HuggingFace token as .hf_token: hf_..."*

   This file is **gitignored** — it is never uploaded to GitHub.

---

## Manual install (without Claude Code)

From the `pka-predictor` folder:

**Windows (Command Prompt):**
```
python -m venv .venv
.venv\Scripts\python -m pip install --upgrade pip
.venv\Scripts\python -m pip install -r requirements.txt
scripts\fetch_assets.bat
run_gui.bat
```

**macOS / Linux:**
```
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
./scripts/fetch_assets.sh
./run_gui.sh
```

Notes:
- `pip install torch` pulls the large default wheel (~2 GB on Windows). For a
  smaller CPU-only torch, install it first with
  `pip install torch --index-url https://download.pytorch.org/whl/cpu`, then the
  rest of `requirements.txt`.
- `fetch_assets` downloads the trained-model bundle (standard models + UMA
  checkpoints + ChEMBL data) from the GitHub Release. One-time.
- On later runs, `run_gui.bat` / `run_gui.sh` skip everything that's already
  done and start in seconds.

---

## Using the app

1. **Enter a SMILES string** (the default is `C1CCCN1`, pyrrolidine; the
   Examples list has a few common amines).
2. **Pick model(s):**
   - **Standard models** (e.g. `std-12C-Morgan-Fingerprints-RF`): fast, work
     offline, no token needed.
   - **UMA models** (`uma-invt` preferred): the most accurate, temperature-aware
     v15.1 production model; needs the HuggingFace token from Step 3.
3. **Set temperature** (default 298.15 K; toggle to Celsius if preferred).
4. Click **Predict**:
   - Standard models show `chembl_pred` (stored ChEMBL features),
     `computed_pred` (features computed live from the SMILES), and the
     experimental `cx_pKa` when known.
   - UMA models show `pKaH1`, `pKaH2`, `pKaH3` (one per protonatable nitrogen)
     and `dH_kJmol` (protonation enthalpy, from the 1/T heads).
5. **UMA temperature sweep** (lower panel): pick a UMA model, set the number of
   points and step, click **Plot sweep** → pKa-vs-T and van't Hoff figures plus
   a table.

**CLI** (same thing, scriptable):
```
run_cli.bat list                                                             :: Windows
run_cli.bat predict --smiles "C1CCCN1" --models uma-invt --temp 298.15
run_cli.bat plot --smiles "C1CNCCN1" --model uma-invt --n 10 --step 10 --unit C
```
(macOS/Linux: `./run_cli.sh ...`.)

**Tips**
- Multi-nitrogen molecules (piperazine `C1CNCCN1`, ethylenediamine `NCCN`) show
  **pKaH1 and pKaH2**; single-nitrogen molecules only pKaH1 — that's correct.
- The **first UMA prediction per molecule** extracts molecular embeddings on CPU
  (~10–60 s); after that it's instant. Everything caches in `cache/` — keep
  that folder.

---

## Docker alternative (optional)

If you'd rather use Docker (e.g. you already have Docker Desktop), the original
container setup is still available:

- Windows: `run_gui_docker.bat` / `run_cli_docker.bat`
- macOS/Linux: `./run_gui_docker.sh` / `./run_cli_docker.sh`

These build the `pkapredict` image from `Dockerfile` (CPU by default; for CUDA:
`docker build --build-arg BASE=pytorch/pytorch:2.8.0-cuda12.6-cudnn9-runtime -t pkapredict .`)
and run the same app in a container. Model assets and the `cache/` folder are
shared with the native install.

---

## Troubleshooting

| Problem | Likely cause / fix |
|---|---|
| `python` not found | Install Python 3.10–3.12 and tick "Add python.exe to PATH" (Windows), then open a **new** terminal. |
| `pip install` fails on `fairchem-core` | Re-run with `DISABLE_CUDA_EXTENSION=1` set, or ask Claude Code to fix the environment. |
| `curl`/`tar` not found (Windows) | Both ship with Windows 10 1803+. On older Windows, use Git Bash and `./run_gui.sh`. |
| UMA prediction fails: "access restricted" / "gated" | Step 3 not done, or `.hf_token` is missing/empty/has a `.txt` suffix. Redo Step 3. |
| First UMA prediction is very slow | Normal — CPU embedding extraction is ~10–60 s/molecule the first time, then cached. |
| Page loads but predictions don't appear | Hard-refresh (**Ctrl+Shift+R**). Check you picked the model family you intended. |
| `fetch_assets` download fails | The release asset may still be uploading — retry later, or set `PKA_ASSETS_URL` to a mirror. |
| Port 7860 already in use | Another copy of the app is running; close it, or run `.venv/bin/python app.py` after editing the port in `cli.py gui --port`. |

---

## Summary checklist

- [ ] Git installed; repo cloned
- [ ] Claude Code installed (or willing to follow *Manual install*)
- [ ] Setup done (venv + dependencies + model bundle) — Claude Code: *"read CLAUDE.md and set up this app"*
- [ ] HuggingFace account + access to `facebook/UMA` approved (UMA models only)
- [ ] Read token saved as `pka-predictor/.hf_token` (one line, no `.txt`)
- [ ] `run_gui.bat` / `./run_gui.sh` opens <http://localhost:7860>
- [ ] A standard-model prediction works (pyrrolidine + `std-12C-Morgan-Fingerprints-RF`)
- [ ] A UMA prediction works (piperazine + `uma-invt`) — confirms the token

---

*Questions? Contact Kamal (aslamkam).*
