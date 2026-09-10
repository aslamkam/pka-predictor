#!/usr/bin/env python3
"""Train all standard-model artifacts with CPU defaults (one shot).

Output: models/standard/<dataset>/<FeatureSet>_<Algo>/{model,scaler,vectorizer}.joblib + meta.json

These are usable prediction artifacts trained with sensible defaults — NOT the
thesis's BO-tuned / RAPIDS-cuml originals (which need GPU + best_params.json that
isn't in the repo). Orca-Sigma is excluded by design.

  python train_standard_models.py [--datasets 12C,10C] [--featuresets ...] [--algos ...]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestRegressor
from sklearn.svm import SVR
from sklearn.neural_network import MLPRegressor
from sklearn.feature_extraction import DictVectorizer  # noqa: F401  (unused; kept for pickled legacy artifacts)
from sklearn.metrics import mean_absolute_error

# Make the package importable when run as a script.
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
os.environ.setdefault("PKA_APP_ROOT", str(HERE))

from pkapredict import config  # noqa: E402
from pkapredict.featurizers import chembl_lookup, registry as featreg  # noqa: E402

try:
    import joblib  # sklearn ships joblib
except ImportError:
    import joblib  # noqa: F811


def _build_xy(dataset: str, featureset: str):
    """Return (X, y, vectorizer-or-None, feat_dim) from the full ChEMBL table."""
    tbl = chembl_lookup._build_table(dataset, featureset)
    tbl["cx_pka"] = pd.to_numeric(tbl.get("cx_pka"), errors="coerce")
    tbl = tbl.dropna(subset=["cx_pka"])
    if tbl.empty:
        return None, None, None, None
    raws = list(tbl["raw"])
    y = tbl["cx_pka"].astype(float).to_numpy()
    # Morgan / Joback / Maginn: stack numeric arrays; pad to a common width.
    arrs = []
    width = 0
    for r in raws:
        a = featreg.vectorize(featureset, r)
        a = np.asarray(a, dtype=float).reshape(-1)
        arrs.append(a)
        width = max(width, a.shape[0])
    X = np.zeros((len(arrs), width), dtype=np.float32)
    for i, a in enumerate(arrs):
        X[i, :a.shape[0]] = a
    return X, y, None, width


# --- model factories -------------------------------------------------------- #
def _make(algo: str, input_dim: int):
    """Sklearn/xgboost estimators (RF/SVR/XGBoost). MLP/CNN are handled directly
    via train_torch in train_one (self-contained torch loop, not SklearnWrapper)."""
    algo = algo.upper()
    if algo == "RF":
        return RandomForestRegressor(n_estimators=120, min_samples_leaf=3,
                                     n_jobs=-1, random_state=42)
    if algo == "SVR":
        return SVR(C=1.0, gamma="scale", kernel="rbf", cache_size=1000)
    if algo == "XGBOOST":
        from xgboost import XGBRegressor
        return XGBRegressor(n_estimators=200, max_depth=6, learning_rate=0.06,
                            subsample=0.8, colsample_bytree=0.8,
                            n_jobs=-1, random_state=42, verbosity=0)
    if algo in ("MLP", "CNN"):
        return None  # sentinel; train_one routes these through train_torch
    raise ValueError(f"unknown algo {algo!r}")


def train_one(dataset: str, featureset: str, algo: str) -> dict:
    X, y, vectorizer, feat_dim = _build_xy(dataset, featureset)
    if X is None:
        return {"status": "no_data", "dataset": dataset, "featureset": featureset, "algo": algo}
    # Cap rows: torch MLP/CNN are CPU-slow on wide Morgan, so cap them lower than
    # RF/XGB. SVR is capped again below (O(n^2)). Override with PKA_TRAIN_MAX_ROWS.
    MAX_ROWS = int(os.environ.get("PKA_TRAIN_MAX_ROWS", "6000"))
    TORCH_ROWS = int(os.environ.get("PKA_TORCH_MAX_ROWS", "3000"))
    cap = TORCH_ROWS if algo.upper() in ("MLP", "CNN") else MAX_ROWS
    if len(y) > cap:
        idx = np.random.RandomState(42).choice(len(y), cap, replace=False)
        X, y = X[idx], y[idx]
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.1, random_state=42)
    if algo.upper() == "SVR" and len(y_tr) > 3000:
        idx = np.random.RandomState(42).choice(len(y_tr), 3000, replace=False)
        X_tr, y_tr = X_tr[idx], y_tr[idx]
    scaler = StandardScaler()
    X_tr_s = scaler.fit_transform(X_tr)
    X_te_s = scaler.transform(X_te)
    model = _make(algo, X_tr_s.shape[1])
    t0 = time.time()
    if algo.upper() in ("MLP", "CNN"):
        from pkapredict.torch_models import train_torch
        # torch CPU is slow on this box; keep epochs small (usable baselines).
        ep = {"MLP": 18, "CNN": 10}[algo.upper()]
        model = train_torch(algo.upper(), X_tr_s, y_tr, epochs=ep,
                            lr=1e-3, batch_size=256, patience=6)
    else:
        model.fit(X_tr_s, y_tr)
    secs = time.time() - t0
    pred = model.predict(X_te_s)
    mae = float(mean_absolute_error(y_te, pred))
    out_dir = config.STANDARD_MODELS_DIR / dataset / f"{featureset}_{algo}"
    out_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, out_dir / "model.joblib")
    joblib.dump(scaler, out_dir / "scaler.joblib")
    if vectorizer is not None:
        joblib.dump(vectorizer, out_dir / "vectorizer.joblib")
    meta = {"dataset": dataset, "featureset": featureset, "algo": algo,
            "feat_dim": int(feat_dim), "n_train": int(len(y_tr)), "test_mae": mae,
            "train_secs": round(secs, 1)}
    (out_dir / "meta.json").write_text(json.dumps(meta, indent=2))
    return {"status": "ok", "out_dir": str(out_dir), "test_mae": mae,
            "n_train": len(y_tr), "feat_dim": feat_dim, "secs": round(secs, 1)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--datasets", default=",".join(config.STANDARD_DATASETS))
    ap.add_argument("--featuresets", default=",".join(config.STANDARD_FEATURESETS))
    ap.add_argument("--algos", default=",".join(config.STANDARD_ALGOS))
    args = ap.parse_args()
    datasets = [d.strip() for d in args.datasets.split(",") if d.strip()]
    featuresets = [f.strip() for f in args.featuresets.split(",") if f.strip()]
    algos = [a.strip() for a in args.algos.split(",") if a.strip()]
    print(f"Training {len(datasets)*len(featuresets)*len(algos)} standard models...")
    for ds in datasets:
        for fs in featuresets:
            for algo in algos:
                try:
                    r = train_one(ds, fs, algo)
                    print(f"  [{ds}/{fs}/{algo}] {r.get('status')} "
                          f"MAE={r.get('test_mae', '-')} dim={r.get('feat_dim', '-')} "
                          f"({r.get('secs', '-')}s)")
                except Exception as e:
                    print(f"  [{ds}/{fs}/{algo}] FAILED: {e}")
    print("done.")


if __name__ == "__main__":
    main()
