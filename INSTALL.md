# pKa Predictor — Setup Guide (for Advisors / New Users)

This guide installs everything from scratch: Docker, the app, and access to the
UMA model. **Allow ~1 hour the first time** (mostly downloads). After that, the
app starts in seconds.

> **What you'll get:** a browser interface at <http://localhost:7860> where you
> type a molecule (as a SMILES string) and get predicted pKa values from 40
> standard ML models and 4 FairChem UMA models, plus temperature-sweep plots.

---

## Prerequisites

- A computer running **Windows 10/11**, **macOS**, or **Linux**.
- ~**5 GB free disk space** (Docker + the model bundle + the UMA checkpoint).
- An internet connection (only needed for setup and the very first prediction).

---

## Step 1 — Install Docker

Docker runs the app in a self-contained container, so you don't need to install
Python or any chemistry libraries yourself.

### Windows
1. Go to <https://www.docker.com/products/docker-desktop/> and download
   **Docker Desktop for Windows**.
2. Run the installer (accept defaults). If asked, enable **WSL 2** (recommended).
3. **Restart your computer** when prompted.
4. Open **Docker Desktop** from the Start menu. Wait until the whale icon in the
   system tray (bottom-right) stops animating and says **"Docker Desktop is running"**.
   - *Note: Docker Desktop is free for personal/academic use. On first launch it
     may ask you to sign in — you can create a free Docker account or click
     **"Continue without signing in"**.*

### macOS
1. Download **Docker Desktop for Mac** from the same link (choose Intel or Apple
   Silicon to match your Mac).
2. Drag **Docker.app** to Applications, open it, wait for the whale icon to say
   it's running.

### Linux
Install Docker Engine for your distribution:
<https://docs.docker.com/engine/install/>. After installing, add yourself to the
`docker` group so you don't need `sudo`:
```
sudo usermod -aG docker $USER
```
Then log out and back in.

**Verify Docker works** by opening a terminal (Command Prompt / PowerShell /
Terminal) and running:
```
docker --version
docker run hello-world
```
If `docker run hello-world` prints "Hello from Docker!", you're set.

---

## Step 2 — Get the app (clone the repository)

You need **Git** installed (<https://git-scm.com/downloads>; on Windows, accept
the defaults — it installs **Git Bash**, which you'll use).

Open a terminal and run:
```
git clone https://github.com/aslamkam/pka-predictor.git
cd pka-predictor
```

This downloads the app code (a few seconds). The large model files are **not** in
the git repository — they download automatically the first time you run the app
(Step 5).

---

## Step 3 — Set up HuggingFace access (for the UMA model) — *required for UMA predictions*

The UMA models use a model checkpoint (`uma-s-1p2`) hosted on HuggingFace that is
**gated** — you must request access once and provide a token. *(The 40 standard
ML models need none of this and work immediately.)*

1. **Create a free HuggingFace account:** <https://huggingface.co/join>
2. **Request access to the model:** go to
   <https://huggingface.co/facebook/UMA> and click **"Acknowledge license"** /
   **"Request access"**. Approval is usually **instant** (automated). Once
   approved, the page will say you have access.
3. **Create an access token:**
   - Go to <https://huggingface.co/settings/tokens>
   - Click **"New token"**
   - **Name:** anything (e.g., `pka-app`)
   - **Type:** select **"Read"** (a read token is enough)
   - Click **"Create"**
   - **Copy the token** (it starts with `hf_...`). You won't be able to see it
     again after you leave the page.
4. **Save the token where the app can find it.** In the `pka_app` folder, create
   a plain-text file named exactly **`.hf_token`** (note the leading dot) and
   paste the token as the **only contents** of the file (one line, no spaces):
   ```
   hf_your_token_here
   ```

   **How to create the file on Windows:**
   - Open **Notepad**.
   - Paste your token (`hf_...`).
   - **File → Save As...**
   - Navigate to the `pka_app` folder.
   - **File name:** `.hf_token` *(type the full name including the dot)*
   - **Save as type:** "All Files (*.*)" *(important — otherwise Notepad adds `.txt`)*
   - Save. The file should appear in the `pka_app` folder.

   This file is **gitignored** — it will never be uploaded to GitHub.

> **If you skip this step:** the standard ML models still work, but the **UMA**
> models will fail with an "access restricted" message.

---

## Step 4 — (Windows only) Confirm `curl` and `tar` are available

These are built into Windows 10 (version 1803 and later) and are used to download
the model bundle on first run. Open **Command Prompt** and run:
```
curl --version
tar --version
```
Both should print a version line. If not (very old Windows), install **Git for
Windows** (<https://git-scm.com/downloads>) and use **Git Bash** to run
`./run_gui.sh` instead of `run_gui.bat`.

---

## Step 5 — Launch the app

### Windows
Double-click **`run_gui.bat`** in the `pka_app` folder.
*(Or, in Command Prompt: `cd` into `pka_app` and run `run_gui.bat`.)*

### macOS / Linux
Open Terminal, `cd` into `pka_app`, and run:
```
./run_gui.sh
```

### What happens on the first launch (be patient — ~20–40 min total):

1. **Downloads the model bundle** (~412 MB compressed → ~728 MB unpacked). This
   includes the 40 trained standard models, the UMA checkpoints, and the ChEMBL
   feature data. *(One-time.)*
2. **Builds the Docker image** (downloads PyTorch + FairChem — several minutes).
   *(One-time.)*
3. **Starts the GUI.** Your browser should open automatically at
   <http://localhost:7860>. If it doesn't, open that URL manually.
4. The **first UMA prediction** downloads the `uma-s-1p2` checkpoint (~1 GB) and
   extracts molecular embeddings (~10–60 s per molecule on CPU). After that, the
   same molecule is instant (cached).

Leave the terminal window open while you use the app — closing it stops the app.
To stop: press **Ctrl-C** in the terminal, or close the window.

### Subsequent launches
Just double-click `run_gui.bat` (or `./run_gui.sh`) again. It starts in
**seconds** — the downloads and image build are skipped.

---

## Step 6 — Using the app

1. **Enter a SMILES string** (the default is `C1CCCN1`, pyrrolidine). The Examples
   list has a few common amines to try.
2. **Pick model(s)** under "Models (pick any)":
   - **Standard models** (e.g., `std-12C-Morgan-Fingerprints-RF`): fast, work
     offline, no token needed. Best for a quick prediction.
   - **UMA models** (`uma-invt` is the preferred one): more accurate, use the
     temperature-aware FairChem model; need the HuggingFace token from Step 3.
3. **Set temperature** (default 298.15 K; toggle unit to Celsius if preferred).
4. Click **Predict**. Results appear in the table:
   - Standard models show `chembl_pred`, `computed_pred`, and the experimental
     `cx_pKa` when known.
   - UMA models show `pKaH1`, `pKaH2`, `pKaH3` (one per protonatable nitrogen),
     and `dH_kJmol` (enthalpy).
5. **UMA temperature sweep** (lower panel): pick a UMA model, set the number of
   points and step, click **Plot sweep**. You get two figures (pKa vs T, and
   van't Hoff) plus a table of pKa values at each temperature.

### Tips
- For multi-nitrogen molecules (diamines like **piperazine** `C1CNCCN1`, or
  **ethylenediamine** `NCCN`), you'll see **pKaH1 and pKaH2** populated.
  Single-nitrogen molecules (like pyrrolidine) only have pKaH1 — that's correct.
- Everything is cached in the `pka_app/cache/` folder; keep it to avoid
  re-extracting embeddings.

---

## Troubleshooting

| Problem | Likely cause / fix |
|---|---|
| `docker: command not found` / "Docker not running" | Start **Docker Desktop** and wait for the whale icon to say "running". |
| `... was unexpected at this time` | You're on an old `run_gui.bat`. Pull the latest code: `git pull`. |
| UMA prediction fails: "access restricted" / "gated" | You skipped Step 3, or the `.hf_token` file is missing/empty/has a `.txt` suffix. Re-do Step 3. |
| `curl`/`tar` not found | See Step 4 — use Git Bash with `./run_gui.sh`. |
| First UMA prediction is very slow | Normal — embedding extraction on CPU is ~10–60 s/molecule the first time, then cached. |
| Page loads but predictions don't appear | Hard-refresh the browser (**Ctrl+Shift+R**). Make sure you're predicting with a model that matches what you want (standard vs UMA). |
| "No such image: pkapredict" | The first-run build failed. Re-run `run_gui.bat`; if it fails again, note the error during the `docker build` step. |

---

## Summary checklist

- [ ] Docker installed and running (`docker run hello-world` works)
- [ ] Git installed; repo cloned; you're in `pka_app/`
- [ ] HuggingFace account created
- [ ] Access to `facebook/UMA` requested and approved
- [ ] Read token created at <https://huggingface.co/settings/tokens>
- [ ] Token saved in `pka_app/.hf_token` (one line, starts with `hf_`, **no `.txt` extension**)
- [ ] `run_gui.bat` (Windows) or `./run_gui.sh` (macOS/Linux) runs and opens <http://localhost:7860>
- [ ] A standard-model prediction works (e.g., pyrrolidine with `std-12C-Morgan-Fingerprints-RF`)
- [ ] A UMA prediction works (e.g., piperazine with `uma-invt`) — confirms token is valid

---

*Questions? Contact Kamal (aslamkam).*
