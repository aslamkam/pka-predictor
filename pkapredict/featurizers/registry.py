"""Featurizer dispatch by feature-set name."""
from __future__ import annotations

from typing import Any
import numpy as np

from . import morgan, joback, benson, maginn, chembl_lookup

MODULES = {
    "Morgan-Fingerprints": morgan,
    "Joback-Reid-Groups": joback,
    "Benson-Groups": benson,
    "Maginn-Sigma-Profile": maginn,
}

LIVE_COMPUTE = {"Morgan-Fingerprints", "Joback-Reid-Groups"}   # SMILES -> feature supported


def featurize(featureset: str, smiles: str):
    """Live-compute a feature from SMILES, or None if unsupported (Benson/Maginn)."""
    mod = MODULES.get(featureset)
    if mod is None:
        return None
    return mod.featurize(smiles)


def decode(featureset: str, text: str):
    mod = MODULES.get(featureset)
    if mod is None:
        return None
    return mod.decode(text)


def vectorize(featureset: str, feature, vectorizer=None) -> np.ndarray:
    mod = MODULES.get(featureset)
    if mod is None:
        raise ValueError(f"unknown featureset {featureset!r}")
    return mod.vectorize(feature, vectorizer)


def lookup(dataset: str, featureset: str, smiles: str) -> dict[str, Any] | None:
    return chembl_lookup.lookup(dataset, featureset, smiles)
