#!/usr/bin/env bash
# Copy the thesis modules + data the app needs into ./repo, making this pka_app/
# dir self-contained for `docker build`, the native install, and for
# zipping/porting. Run once on the Linux dev box (the thesis repo is the parent
# dir). Safe to re-run (wipes ./repo first).
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/.." && pwd)"          # thesis repo root (parent of pka_app)
DST="$HERE/repo"
echo "Copying thesis deps from $REPO -> $DST"

rm -rf "$DST"
mkdir -p "$DST"
# Shared repo-root module (SklearnWrapper).
cp "$REPO/pytorch_sklearn_wrapper.py" "$DST/"

# Basicity pKa model source + the leak-free relaxed PRODUCTION v15.1 run dirs
# (4 temperature heads x 3 split seeds, retrained 2026-08-13 on the amino-acid-
# fixed v15.1 corpus). Only the inference artifacts are copied (Stage-3 seed
# checkpoints + the run scaler) — stage1/stage2 weights and eval dumps are not
# needed at predict time and would bloat the release bundle.
BPDST="$DST/Primary_Research/Scoring_Models/Basicity_pKa_2"
mkdir -p "$BPDST/runs"
for f in model.py engine.py data.py data_relaxed.py data_combined.py infer.py; do
  cp "$REPO/Primary_Research/Scoring_Models/Basicity_pKa_2/$f" "$BPDST/" 2>/dev/null || true
done
for tag in lfv15 lfv15linear lfv15invt lfv15invtlnt; do
  for s in 42 777 123; do
    d="$(ls -d "$REPO"/Primary_Research/Scoring_Models/Basicity_pKa_2/runs/exp_relaxed_${tag}_s${s}_* 2>/dev/null | head -1 || true)"
    if [ -n "$d" ]; then
      name="$(basename "$d")"
      mkdir -p "$BPDST/runs/$name/stage3"
      cp "$d/scaler.joblib" "$BPDST/runs/$name/"
      for sd in "$d"/stage3/seed_*; do
        [ -f "$sd/checkpoint.pt" ] || continue
        mkdir -p "$BPDST/runs/$name/stage3/$(basename "$sd")"
        cp "$sd/checkpoint.pt" "$BPDST/runs/$name/stage3/$(basename "$sd")/"
      done
    else
      echo "  WARN: no run dir for tag=$tag seed=$s"
    fi
  done
done

# FairChem relaxed extraction pipeline (not the multi-GB embeddings — those are
# extracted on demand into the cache dir at runtime).
mkdir -p "$DST/DFT/FairChem"
cp "$REPO/DFT/FairChem/uma_relaxed_pipeline.py" "$DST/DFT/FairChem/" 2>/dev/null || true

# ChEMBL feature CSVs (12C + 10C) + master amines CSV, for the 3 feature sets
# (Benson-Groups dropped: its RMG generator only runs in a Linux Docker
# container, which the native Windows install does not have).
for ds in 12C 10C; do
  srcbase="$REPO/Features/Chembl35_${ds}_CX_Basic_pKa"
  dstbase="$DST/Features/Chembl35_${ds}_CX_Basic_pKa"
  mkdir -p "$dstbase"
  cp "$srcbase/chembl35_${ds}_amines.csv" "$dstbase/" 2>/dev/null || true
  for fs in Morgan-Fingerprints Joback-Reid-Groups Maginn-Sigma-Profile; do
    if [ -d "$srcbase/$fs" ]; then
      mkdir -p "$dstbase/$fs"
      cp -r "$srcbase/$fs/." "$dstbase/$fs/"
    fi
  done
done

echo "Bundle prepared. Size:"
du -sh "$DST" || true
