#!/usr/bin/env bash
# Copy the thesis modules + data the app needs into ./repo, making this pka_app/
# dir self-contained for `docker build` and for zipping/porting. Run once on the
# Linux dev box (the thesis repo is the parent dir). Safe to re-run.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/.." && pwd)"          # thesis repo root (parent of pka_app)
DST="$HERE/repo"
echo "Copying thesis deps from $REPO -> $DST"

mkdir -p "$DST"
# Shared repo-root module (SklearnWrapper).
cp "$REPO/pytorch_sklearn_wrapper.py" "$DST/"

# Basicity pKa model source + the leak-free relaxed run checkpoints (4 heads x 3 seeds).
BPDST="$DST/Primary_Research/Scoring_Models/Basicity_pKa_2"
mkdir -p "$BPDST/runs"
for f in model.py engine.py data.py data_relaxed.py data_combined.py infer.py; do
  cp "$REPO/Primary_Research/Scoring_Models/Basicity_pKa_2/$f" "$BPDST/" 2>/dev/null || true
done
for h in tbaseline vanthoff vanthoffinvt vanthoffinvtlnt; do
  for s in 42 777 123; do
    d="$(ls -d "$REPO"/Primary_Research/Scoring_Models/Basicity_pKa_2/runs/exp_relaxed_lf${h}_s${s}_* 2>/dev/null | head -1 || true)"
    if [ -n "$d" ]; then
      cp -r "$d" "$BPDST/runs/"
    else
      echo "  WARN: no run dir for head=$h seed=$s"
    fi
  done
done

# FairChem relaxed extraction pipeline (not the multi-GB embeddings — those are
# extracted on demand into the mounted /cache volume at runtime).
mkdir -p "$DST/DFT/FairChem"
cp "$REPO/DFT/FairChem/uma_relaxed_pipeline.py" "$DST/DFT/FairChem/" 2>/dev/null || true

# ChEMBL feature CSVs (12C + 10C) + master amines CSV, for the 4 feature sets.
for ds in 12C 10C; do
  srcbase="$REPO/Features/Chembl35_${ds}_CX_Basic_pKa"
  dstbase="$DST/Features/Chembl35_${ds}_CX_Basic_pKa"
  mkdir -p "$dstbase"
  cp "$srcbase/chembl35_${ds}_amines.csv" "$dstbase/" 2>/dev/null || true
  for fs in Morgan-Fingerprints Joback-Reid-Groups Benson-Groups Maginn-Sigma-Profile; do
    if [ -d "$srcbase/$fs" ]; then
      mkdir -p "$dstbase/$fs"
      cp -r "$srcbase/$fs/." "$dstbase/$fs/"
    fi
  done
done

echo "Bundle prepared. Size:"
du -sh "$DST" || true
