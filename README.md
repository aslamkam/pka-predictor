# pKa Predictor

Predict pKa from a SMILES string with the thesis's **standard ML models** or the
**FairChem UMA Basicity** model, via a browser GUI (Linux + Windows) or a Docker
CLI. Inputs and outputs are cached to disk, so a repeat prediction is instant.

> ### 📖 New here? See **[INSTALL.md](INSTALL.md)** for a full setup walkthrough
> from zero (Docker install, HuggingFace account + token for the UMA model,
> first launch, troubleshooting). The Quick start below is for those who already
> have Docker.

* **40 standard models** — ChEMBL 12C **and** 10C amine sets × {Morgan
  fingerprints, Joback-Reid groups, Benson groups, Maginn sigma profile} ×
  {MLP, Random Forest, SVR, XGBoost, CNN}. (Orca sigma is excluded.)
* **4 UMA variants** — the relaxed-route FairChem `uma-s-1p2` Basicity model's
  temperature heads: `none` (standard), `linear` (linear-in-T), `invt`
  (linear-in-1/T, preferred), `invtlnt` (1/T+lnT, constant ΔCp°). Each is the
  3-split-seed × 5-Stage-3 ensemble. UMA predicts **pKaH1, pKaH2, pKaH3** and
  reads ΔH° (and ΔCp°) directly from the 1/T heads.

## Quick start (GUI)

1. Install **Docker** (Docker Desktop on Windows).
2. Double-click **`run_gui.bat`** (Windows) or run **`./run_gui.sh`** (Linux).
   * **First run** downloads the model assets bundle (~728 MB: the 40 trained
     standard models + UMA checkpoints + ChEMBL CSVs — shipped via GitHub
     Release, so the git clone stays small), then builds the Docker image
     (downloads torch + fairchem — a few minutes). The `uma-s-1p2` checkpoint
     (~1 GB) downloads on first UMA prediction and is cached.
   * Later runs skip the download and start in seconds.
3. Your browser opens at <http://localhost:7860>. Enter a SMILES, pick models,
   set temperature (default **Kelvin**; toggle to Celsius), click **Predict**.
4. For UMA, use the **temperature sweep** panel: choose #points + step + unit,
   click **Plot** → pKa-vs-T and van't-Hoff (ln K_a vs 1/T) figures for
   pKaH1/H2/H3 (thesis Fig. 6.4 style).

Everything persists in **`./cache/`** (predictions, extracted UMA embeddings, and
the uma-s-1p2 download) — keep that folder to avoid re-extraction.

### HuggingFace token (required for UMA models)

The **UMA** models use FairChem's `facebook/UMA` (`uma-s-1p2`) checkpoint, which
is **gated** — you must (once) accept its license, then provide a token so the
first prediction can download it. The standard ML models need no token.

1. Create a free HuggingFace account, then request access at
   <https://huggingface.co/facebook/UMA> (approval is usually instant).
2. Create an access token at <https://huggingface.co/settings/tokens>
   (a **read** token is enough).
3. Put it in **one** of these places (the launchers check both):
   * a `pka_app/.hf_token` file containing just the token (one line; this file
     is gitignored so it never gets committed) — easiest for double-clicking
     `run_gui.bat`; **or**
   * an `HF_TOKEN` environment variable.

   The launchers pass the token into the container via `--env-file` (so it never
   appears in `ps`/process listings) and delete the temp file afterwards. If no
   token is found, the GUI still runs, but UMA predictions will fail with an
   access error; standard models are unaffected.

## CLI (Docker)

```bash
./run_cli.sh list
./run_cli.sh predict --smiles "C1CCCN1" --models uma-invt,std-12C-Morgan-Fingerprints-RF --temp 298.15 --unit K
./run_cli.sh plot   --smiles "C1CCCN1" --model uma-invt --n 10 --step 10 --unit C --out plots
```
(Windows: `run_cli.bat ...`.) `predict` prints JSON and caches; `plot` writes the
two PNG sets. Temperature defaults to Kelvin; `--unit C` interprets `--temp` (and
the plot axis) as Celsius.

## Standard models — three predictions side by side

For each standard model the table shows three pKa numbers:

* **chembl_pred** — using the SMILES's *stored* ChEMBL feature row (only if the
  SMILES is in the ChEMBL amine set).
* **computed_pred** — using features *we compute* from the SMILES. Live compute
  is supported for **Morgan** (RDKit) and **Joback** (SMARTS table). **Benson**
  and **Maginn** have no live compute (they need the RMG container / a GCN
  model) — for those, use ChEMBL lookup or paste a vector.
* **pasted_pred** — from a feature vector you paste (the *Optional* panel). For
  Benson paste the `defaultdict(...)` group dict; for Maginn/Morgan/Joback paste
  the numeric vector / bitstring.

…plus the experimental **CX Basic pKa** label when the SMILES is known.

> ⚠️ The standard models here are **retrained with CPU defaults** (RF/XGB/SVR +
> a torch MLP/CNN), **not** the thesis's GPU-BO-tuned / RAPIDS-cuml originals.
> They are usable prediction artifacts; expect MAE ≈ 0.8–1.5 pKa units (RF/XGB
> best). Re-run `train_standard_models.py` to regenerate.

## UMA — what it does

Builds the 1158-D relaxed feature vector (`base_global | prot_global | base_local
| prot_local | Δglobal | T_norm | solvent`) from `uma-s-1p2` penultimate
embeddings of the neutral + H1/H2/H3 protonated forms, then ensemble-predicts.
The protonation ladder is generated by an RDKit heuristic (best on the aliphatic
amine / diamine / amino-alcohol CCUS domain; exotic aromatics may fall back to
H1-only with a warning). On CPU, embedding extraction is ~10–60 s per molecule
the first time, then cached.

Temperature enters as `T_norm = (T_C − 25)/10`; the van't Hoff plot uses absolute
temperature (`1/T` with T in Kelvin). ΔH°/ΔCp° are read directly from the 1/T
head's coefficients (no refit).

## Layout

```
pka_app/
  cli.py  app.py  train_standard_models.py  prepare_bundle.sh
  Dockerfile  run_gui.{sh,bat}  run_cli.{sh,bat}  requirements.txt
  scripts/           # fetch_assets.{sh,bat} (one-time ~728 MB download on first
                     #   run) + publish_release.sh (rebuilds the asset bundle)
  pkapredict/        # the package (config, cache, smiles_util, featurizers,
                     #   standard_models, uma/{calculator,extract,predict}, plotting, core)
  models/standard/   # trained standard-model artifacts (joblib) — NOT in git;
                     #   fetched from the GitHub Release on first run
  repo/              # vendored thesis deps for Docker (Basicity_pKa_2 source +
                     #   run checkpoints + uma_relaxed_pipeline + ChEMBL CSVs) —
                     #   also fetched from the Release on first run
  cache/             # predictions + extracted UMA embeddings (mounted as /cache)
```

> The `models/` and `repo/` trees (the model binaries, ~728 MB) are deliberately
> excluded from git and shipped as a **GitHub Release asset** — fetched
> automatically by `scripts/fetch_assets.{sh,bat}` on first run. This keeps the
> clone small and avoids Git-LFS quota limits. To (re)build and upload the asset,
> run `scripts/publish_release.sh` (needs the `gh` CLI).

## Develop (no Docker)

Run from this `pka_app/` dir inside the thesis repo (so `Features/`,
`Primary_Research/…/Basicity_pKa_2/`, `DFT/FairChem/` resolve):

```bash
micromamba run -n fairchem_cpu python train_standard_models.py   # build the 40 artifacts
micromamba run -n fairchem_cpu python cli.py predict --smiles "C1CCCN1" --models uma-invt --temp 298.15
micromamba run -n fairchem_cpu pip install gradio                # only for the local GUI
micromamba run -n fairchem_cpu python app.py
```

## Caveats

* Orca-sigma models are intentionally excluded.
* The uma-s-1p2 checkpoint (~1 GB) downloads on first UMA use (into `./cache`).
* GPU is optional: the default image is CPU (no GPU or CUDA drivers required —
  it runs anywhere Docker does). For CUDA, rebuild with
  `docker build --build-arg BASE=pytorch/pytorch:2.8.0-cuda12.6-cudnn9-runtime -t pkapredict .`
  (faster embedding extraction).
