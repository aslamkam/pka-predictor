"""Maginn sigma profile — a fixed-length float vector stored as a Python list
repr in the ``El_Sigma_Profile`` column (ML/El-GCN generated).

Live compute from SMILES is NOT available (needs the GCN generator); served by
ChEMBL lookup or a pasted vector.
"""
from __future__ import annotations

import ast
import numpy as np


def parse_array(text) -> np.ndarray:
    try:
        return np.asarray(ast.literal_eval(text), dtype=float)
    except Exception:
        return np.asarray([])


def featurize(smiles: str):  # no live compute
    return None


def decode(text: str) -> np.ndarray | None:
    if not text:
        return None
    arr = parse_array(text)
    return arr if arr.size else None


def vectorize(feature, vectorizer=None) -> np.ndarray:
    return np.asarray(feature, dtype=float)
