"""Load a trained standard-model artifact and predict pKa from a raw feature.

Each artifact dir (models/standard/<dataset>/<FeatureSet>_<Algo>/) holds:
  - model.joblib      : trained estimator (.predict(X) where X is the scaled matrix)
  - scaler.joblib     : StandardScaler / MinMaxScaler (or None)
  - vectorizer.joblib : optional feature vectorizer (None for the current feature sets)
  - meta.json         : featureset, algo, dataset, feat_dim, train_mae, n_train
"""
from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np

from . import config
from .featurizers import registry as featreg


def artifact_dir_for(model_id: str) -> Path:
    e = config.REGISTRY_BY_ID[model_id]
    return e["artifact_dir"]


class StandardModel:
    def __init__(self, model_id: str):
        self.model_id = model_id
        e = config.REGISTRY_BY_ID[model_id]
        self.featureset = e["featureset"]
        self.dataset = e["dataset"]
        self.algo = e["algo"]
        d = e["artifact_dir"]
        self.model_path = d / "model.joblib"
        self.scaler_path = d / "scaler.joblib"
        self.vectorizer_path = d / "vectorizer.joblib"
        self.meta_path = d / "meta.json"
        self._loaded = False
        self.model = None
        self.scaler = None
        self.vectorizer = None
        self.meta = {}

    def exists(self) -> bool:
        return self.model_path.exists()

    def load(self):
        if self._loaded:
            return self
        if not self.model_path.exists():
            raise FileNotFoundError(f"no trained artifact at {self.model_path}")
        self.model = joblib.load(self.model_path)
        self.scaler = joblib.load(self.scaler_path) if self.scaler_path.exists() else None
        self.vectorizer = (joblib.load(self.vectorizer_path)
                           if self.vectorizer_path.exists() else None)
        if self.meta_path.exists():
            self.meta = json.loads(self.meta_path.read_text())
        self._loaded = True
        return self

    def predict_raw(self, raw_feature) -> float | None:
        """Vectorize -> scale -> model.predict. Returns a single pKa float."""
        self.load()
        try:
            vec = featreg.vectorize(self.featureset, raw_feature, self.vectorizer)
        except Exception:
            return None
        X = np.asarray(vec, dtype=float).reshape(1, -1)
        # Align feature dim to the trained model's expectation (pad/truncate).
        dim = self.meta.get("feat_dim")
        if isinstance(dim, int) and dim > 0 and X.shape[1] != dim:
            X = _resize(X, dim)
        if self.scaler is not None:
            try:
                X = self.scaler.transform(X)
            except Exception:
                pass
        pred = self.model.predict(X)
        return float(np.asarray(pred).reshape(-1)[0])


def _resize(X: np.ndarray, dim: int) -> np.ndarray:
    cur = X.shape[1]
    if cur == dim:
        return X
    out = np.zeros((X.shape[0], dim), dtype=float)
    out[:, :min(cur, dim)] = X[:, :min(cur, dim)]
    return out


_MODEL_CACHE: dict[str, StandardModel] = {}


def get_model(model_id: str) -> StandardModel:
    if model_id not in _MODEL_CACHE:
        _MODEL_CACHE[model_id] = StandardModel(model_id)
    return _MODEL_CACHE[model_id]
