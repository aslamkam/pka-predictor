"""Paths, constants, and the model registry for the pKa predictor app.

Paths are resolved relative to this package by default (so the app works both
in-repo during development and when the repo is copied into /app in Docker), and
can be overridden with the env vars ``PKA_APP_ROOT`` and ``PKA_REPO_ROOT``.
"""
from __future__ import annotations

import os
from pathlib import Path

PKG_DIR = Path(__file__).resolve().parent            # .../pka_app/pkapredict
APP_ROOT = Path(os.environ.get("PKA_APP_ROOT") or PKG_DIR.parent).resolve()
REPO_ROOT = Path(os.environ.get("PKA_REPO_ROOT") or PKG_DIR.parents[1]).resolve()

# --- thesis-repo locations (read-only inputs) ------------------------------- #
BASICITY_DIR = REPO_ROOT / "Primary_Research" / "Scoring_Models" / "Basicity_pKa_2"
RELAXED_EMB_DIR = REPO_ROOT / "DFT" / "FairChem" / "Relaxed_Embeddings"
FAIRCHEM_PIPELINE = REPO_ROOT / "DFT" / "FairChem" / "uma_relaxed_pipeline.py"
FEATURES_DIR = REPO_ROOT / "Features"

# Relaxed embedding subdirs (where get_relaxed_embeddings writes / reads).
GLOBAL_EMB_DIR = RELAXED_EMB_DIR / "Global_Embeddings"
LOCAL_EMB_DIR = RELAXED_EMB_DIR / "Local_Node_Embeddings"
# In Docker / a fresh checkout we let the user point extraction output at a
# writable, persisted location (the mounted cache volume) so freshly-extracted
# embeddings survive container restarts.
EMB_GLOBAL_DIR = Path(os.environ.get("PKA_EMB_GLOBAL_DIR") or GLOBAL_EMB_DIR)
EMB_LOCAL_DIR = Path(os.environ.get("PKA_EMB_LOCAL_DIR") or LOCAL_EMB_DIR)

# --- app-owned locations (writable outputs) -------------------------------- #
MODELS_DIR = APP_ROOT / "models"
STANDARD_MODELS_DIR = MODELS_DIR / "standard"
CACHE_DIR = Path(os.environ.get("PKA_CACHE_DIR") or (APP_ROOT / "cache"))
PREDICTION_CACHE_DIR = CACHE_DIR / "predictions"
PLOTS_DIR = CACHE_DIR / "plots"

for _d in (CACHE_DIR, PREDICTION_CACHE_DIR, PLOTS_DIR, STANDARD_MODELS_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# --- physics / chemistry constants ----------------------------------------- #
T0_K = 273.15                       # Celsius -> Kelvin offset
R_GAS = 8.314462618                 # J/(mol K)
LN10 = 2.302585092994046           # ln K_a = -LN10 * pKa
DEFAULT_T_K = 298.15               # GUI default temperature (Kelvin)

# Water solvent descriptors (the aqueous target domain; from temperature_holdout.csv).
WATER_SOLVENT = {
    "Solvent": "O",
    "Eps": 78.36,
    "Inv_Eps": 1.0 / 78.36,
    "Alpha": 1.17,
    "Beta": 0.47,
    "PiStar": 1.09,
}

# --- model families -------------------------------------------------------- #
STANDARD_DATASETS = ["12C", "10C"]
# Orca-Sigma-Profile is intentionally excluded (needs ORCA DFT; user decision).
# Benson-Groups is excluded: its group-count generator is RMG, which only runs
# in the (Linux) RMG Docker container — dropping it is what allows the native
# no-Docker Windows install.
STANDARD_FEATURESETS = [
    "Morgan-Fingerprints",
    "Joback-Reid-Groups",
    "Maginn-Sigma-Profile",
]
STANDARD_ALGOS = ["MLP", "RF", "SVR", "XGBoost", "CNN"]

# UMA temperature heads -> (glob suffix under Basicity_pKa_2/runs, split seeds).
# These are the PRODUCTION v15.1 retrains (2026-08-13, amino-acid-fixed corpus;
# CCUS MAE 0.272 +/-0.007 for the standard head) — runs tagged `lfv15*`.
# There are no v15 90/10-split variants; the old v13 80/20+90/10 bundles were
# superseded by these. Each head is the 3 split-seed x 5 Stage-3-seed ensemble.
UMA_HEADS = {
    "none":    {"glob": "exp_relaxed_lfv15_s{s}_*",        "seeds": [42, 777, 123]},
    "linear":  {"glob": "exp_relaxed_lfv15linear_s{s}_*",  "seeds": [42, 777, 123]},
    "invt":    {"glob": "exp_relaxed_lfv15invt_s{s}_*",    "seeds": [42, 777, 123]},
    "invtlnt": {"glob": "exp_relaxed_lfv15invtlnt_s{s}_*", "seeds": [42, 777, 123]},
}
UMA_HEAD_LABELS = {
    "none":    "UMA v15.1 — standard head (best CCUS accuracy)",
    "linear":  "UMA v15.1 — linear-in-T head",
    "invt":    "UMA v15.1 — linear-in-1/T head (preferred for temperature)",
    "invtlnt": "UMA v15.1 — 1/T + lnT head (constant ΔCp°)",
}


def _resolve_uma_run_dirs() -> dict[str, list[Path]]:
    """Resolve, per head, the concrete split-seed run dirs that actually exist."""
    out: dict[str, list[Path]] = {}
    runs_root = BASICITY_DIR / "runs"
    for head, spec in UMA_HEADS.items():
        dirs: list[Path] = []
        for s in spec["seeds"]:
            hits = sorted(runs_root.glob(spec["glob"].format(s=s)))
            if hits:
                dirs.append(hits[-1])          # latest jobid suffix
        out[head] = dirs
    return out


def build_registry() -> list[dict]:
    """The full chooser registry: 30 standard + 4 UMA entries."""
    reg: list[dict] = []
    for ds in STANDARD_DATASETS:
        for fs in STANDARD_FEATURESETS:
            for algo in STANDARD_ALGOS:
                reg.append({
                    "id": f"std-{ds}-{fs}-{algo}",
                    "family": "standard",
                    "dataset": ds,
                    "featureset": fs,
                    "algo": algo,
                    "label": f"{ds} · {fs} · {algo}",
                    "artifact_dir": STANDARD_MODELS_DIR / ds / f"{fs}_{algo}",
                })
    for head, label in UMA_HEAD_LABELS.items():
        reg.append({
            "id": f"uma-{head}",
            "family": "uma",
            "head": head,
            "label": label,
        })
    return reg


REGISTRY = build_registry()
REGISTRY_BY_ID = {e["id"]: e for e in REGISTRY}
UMA_RUN_DIRS = _resolve_uma_run_dirs()


def standard_feature_csv(dataset: str, featureset: str) -> Path | None:
    """Locate the ChEMBL feature CSV for a (dataset, featureset) pair."""
    base = FEATURES_DIR / f"Chembl35_{dataset}_CX_Basic_pKa" / featureset
    # Keep this in sync with the train loader + the ChEMBL lookup.
    candidates = {
        "Morgan-Fingerprints": [base / "bits2048" / "radius2"],
        "Joback-Reid-Groups":  [base],
        "Maginn-Sigma-Profile":[base / "El_GCN"],
    }.get(featureset, [base])
    name_hints = {
        "Morgan-Fingerprints": "bits2048_radius2_MFP.csv",
        "Joback-Reid-Groups":  "_JRG.csv",
        "Maginn-Sigma-Profile":"_El_GCN_SP.csv",
    }.get(featureset, "")
    for c in candidates:
        if c.is_dir():
            csvs = sorted(c.glob("*.csv"))
            preferred = [p for p in csvs if name_hints in p.name and "depricated" not in p.name]
            if preferred:
                return preferred[0]
            non_dep = [p for p in csvs if "depricated" not in p.name and "deprecated" not in p.name]
            if non_dep:
                return non_dep[0]
    return None
