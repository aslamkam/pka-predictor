# pKa Predictor

Predict pKa from a SMILES string with the thesis's **standard ML models** or the
**FairChem UMA v15.1 Basicity** model, via a browser GUI or CLI — installed
**natively on Windows/macOS/Linux (no Docker required)**, with Docker as an
optional alternative. Inputs and outputs are cached to disk, so a repeat
prediction is instant.

> ### 📖 New here? See **[INSTALL.md](INSTALL.md)** for the full setup
> walkthrough. The recommended path is to let **[Claude Code](https://claude.com/claude-code)**
> do the setup — this repo ships a **[CLAUDE.md](CLAUDE.md)** with exact
> machine-readable instructions. Clone the repo, run `claude` in the folder,
> and say *"read CLAUDE.md and set up this app"*.

* **30 standard models** — ChEMBL 12C **and** 10C amine sets × {Morgan
  fingerprints, Joback-Reid groups, Maginn sigma profile} × {MLP, Random
  Forest, SVR, XGBoost, CNN}. (Orca sigma is excluded; **Benson groups were
  dropped** — their RMG feature generator only runs inside a Linux Docker
  container, and dropping them is what makes the native Windows install
  possible.)
* **4 UMA variants** — the **production v15.1 retrain** (2026-08-13,
  amino-acid-fixed corpus) of the relaxed-route FairChem `uma-s-1p2` Basicity
  model's temperature heads: `none` (standard; best CCUS accuracy, MAE
  **0.272 ±0.007**), `linear` (linear-in-T), `invt` (linear-in-1/T, preferred
  for temperature work), `invtlnt` (1/T+lnT, constant ΔCp°). Each is the
  3-split-seed × 5-Stage-3-seed ensemble. UMA predicts **pKaH1, pKaH2, pKaH3**
  and reads ΔH° (and ΔCp°) directly from the 1/T heads.

## Quick start (native, no Docker)

1. Install **Python 3.10–3.12** and **Git**, then clone this repo.
2. Easiest: run `claude` in the repo folder and say *"read CLAUDE.md and set up
   this app"*. By hand instead:
   * **Windows:** double-click **`run_gui.bat`**.
   * **macOS/Linux:** **`./run_gui.sh`**.
   * First run creates `.venv`, installs `requirements.txt`, and downloads the
     model-assets bundle (several hundred MB, shipped via GitHub Release so the
     git clone stays small). Later runs start in seconds.
3. Your browser opens at <http://localhost:7860>. Enter a SMILES, pick models,
   set temperature (default **Kelvin**; toggle to Celsius), click **Predict**.
4. For UMA, use the **temperature sweep** panel: choose #points + step + unit,
   click **Plot sweep** → pKa-vs-T and van't-Hoff (ln K_a vs 1/T) figures for
   pKaH1/H2/H3.

Everything persists in **`./cache/`** (predictions, extracted UMA embeddings,
and the uma-s-1p2 download) — keep that folder to avoid re-extraction.

### HuggingFace token (required for UMA models)

The **UMA** models use FairChem's `facebook/UMA` (`uma-s-1p2`) checkpoint, which
is **gated** — you must (once) accept its license, then provide a token so the
first prediction can download it. The standard ML models need no token.

1. Create a free HuggingFace account, then request access at
   <https://huggingface.co/facebook/UMA> (approval is usually instant).
2. Create a **read** access token at <https://huggingface.co/settings/tokens>.
3. Put it in **one** of these places (the launchers check both):
   * a `.hf_token` file in this folder containing just the token (one line;
     gitignored so it never gets committed); **or**
   * an `HF_TOKEN` environment variable.

If no token is found, the GUI still runs, but UMA predictions will fail with an
access error; standard models are unaffected.

## CLI

```bash
# Windows: run_cli.bat ...   |   macOS/Linux: ./run_cli.sh ...
run_cli.bat list
run_cli.bat predict --smiles "C1CCCN1" --models uma-invt,std-12C-Morgan-Fingerprints-RF --temp 298.15 --unit K
run_cli.bat plot   --smiles "C1CCCN1" --model uma-invt --n 10 --step 10 --unit C --out plots
```

`predict` prints JSON and caches; `plot` writes the two PNG sets. Temperature
defaults to Kelvin; `--unit C` interprets `--temp` (and the plot axis) as
Celsius.

## Standard models — three predictions side by side

For each standard model the table shows three pKa numbers:

* **chembl_pred** — using the SMILES's *stored* ChEMBL feature row (only if the
  SMILES is in the ChEMBL amine set).
* **computed_pred** — using features *we compute* from the SMILES. Live compute
  is supported for **Morgan** (RDKit) and **Joback** (SMARTS table). **Maginn**
  has no live compute (it needs a GCN model) — for it, use ChEMBL lookup or
  paste a vector.
* **pasted_pred** — from a feature vector you paste (the *Optional* panel).

…plus the experimental **CX Basic pKa** label when the SMILES is known.

> ⚠️ The standard models here are **retrained with CPU defaults** (RF/XGB/SVR +
> a torch MLP/CNN), **not** the thesis's GPU-BO-tuned / RAPIDS-cuml originals.
> They are usable prediction artifacts; expect MAE ≈ 0.8–1.5 pKa units (RF/XGB
> best). Re-run `train_standard_models.py` to regenerate.

## UMA — what it does

Builds the 1158-D relaxed feature vector (`base_global | prot_global | base_local
| prot_local | Δglobal | T_norm | solvent`) from `uma-s-1p2` penultimate
embeddings of the neutral + H1/H2/H3 protonated forms, then ensemble-predicts
with the **v15.1 production checkpoints** (`exp_relaxed_lfv15*` runs of the
thesis's `Basicity_pKa_2` module). The protonation ladder is generated by an
RDKit heuristic (best on the aliphatic amine / diamine / amino-alcohol CCUS
domain; exotic aromatics may fall back to H1-only with a warning). On CPU,
embedding extraction is ~10–60 s per molecule the first time, then cached.

Temperature enters as `T_norm = (T_C − 25)/10`; the van't Hoff plot uses absolute
temperature (`1/T` with T in Kelvin). ΔH°/ΔCp° are read directly from the 1/T
head's coefficients (no refit).

## Docker (optional alternative)

The original containerized setup is kept as `run_gui_docker.{sh,bat}` /
`run_cli_docker.{sh,bat}` + `Dockerfile` (CPU image by default; for CUDA:
`docker build --build-arg BASE=pytorch/pytorch:2.8.0-cuda12.6-cudnn9-runtime -t pkapredict .`).
Model assets and `cache/` are shared with the native install.

## Layout

```
pka_app/
  cli.py  app.py  train_standard_models.py  prepare_bundle.sh  CLAUDE.md
  Dockerfile  run_gui.{sh,bat}  run_cli.{sh,bat}              # native launchers
  run_gui_docker.{sh,bat}  run_cli_docker.{sh,bat}            # Docker variants
  requirements.txt
  scripts/           # fetch_assets.{sh,bat} (one-time model-bundle download on
                     #   first run) + publish_release.sh (rebuilds the bundle)
  pkapredict/        # the package (config, cache, smiles_util, featurizers,
                     #   standard_models, uma/{calculator,extract,predict}, plotting, core)
  models/standard/   # trained standard-model artifacts (joblib) — NOT in git;
                     #   fetched from the GitHub Release on first run
  repo/              # vendored thesis deps (Basicity_pKa_2 source + v15.1 Stage-3
                     #   checkpoints + uma_relaxed_pipeline + ChEMBL CSVs) —
                     #   also fetched from the Release on first run
  cache/             # predictions + extracted UMA embeddings (+ HF download)
```

> The `models/` and `repo/` trees are deliberately excluded from git and shipped
> as a **GitHub Release asset** (`v2.0-models`) — fetched automatically by
> `scripts/fetch_assets.{sh,bat}` on first run. To (re)build and upload the
> asset, run `prepare_bundle.sh` then `scripts/publish_release.sh` (needs the
> `gh` CLI).

## Develop

Run from this `pka_app/` dir inside the thesis repo (so `Features/`,
`Primary_Research/…/Basicity_pKa_2/`, `DFT/FairChem/` resolve) with the thesis's
`fairchem_cpu` conda env, or natively via the `.venv` the launchers create:

```bash
micromamba run -n fairchem_cpu python train_standard_models.py   # build the 30 artifacts
micromamba run -n fairchem_cpu python cli.py predict --smiles "C1CCCN1" --models uma-invt --temp 298.15
micromamba run -n fairchem_cpu pip install gradio                # only for the local GUI
micromamba run -n fairchem_cpu python app.py
```

## Caveats

* Orca-sigma and Benson-group models are intentionally excluded (see above).
* The uma-s-1p2 checkpoint (~1 GB) downloads on first UMA use (into `./cache`).
* GPU is optional: the native install and the default Docker image are CPU-only.
  For CUDA, either install a CUDA torch wheel into `.venv`, or rebuild the
  Docker image with the `BASE` build-arg shown above.

## Working as a submodule (development)

This repo is tracked in the thesis repo (`jules_experiment`) as a **git
submodule** at `pka_app/`, so the agent edits thesis files and app code in one
tree while the app's canonical history lives here (`aslamkam/pka-predictor`).

**Updating the app code (e.g. new models):**
```bash
# 1) edit + commit in the submodule, push to pka-predictor
cd pka_app
git add . && git commit -m "..." && git push

# 2) back in the parent, bump the submodule pointer and push
cd ..
git add pka_app
git commit -m "Bump pka_app submodule" && git push
```

**After a fresh clone of `jules_experiment`:**
```bash
git clone https://github.com/aslamkam/jules_experiment.git
cd jules_experiment
git submodule update --init --recursive     # populates pka_app/
```

The gitignored binaries (`models/`, `repo/`, `cache/`, `.venv/`, `.hf_token`)
are **not** in either git repo — run `run_gui.bat`/`run_gui.sh` once to fetch
the model-bundle release asset (or restore a local backup) before developing.
