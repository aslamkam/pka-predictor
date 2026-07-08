"""Benson groups — stored as an RMG ``defaultdict`` repr (group name -> count).

Live compute from SMILES is NOT available (needs the RMG container); served by
ChEMBL lookup or a pasted ``defaultdict``/dict literal. Vectorization uses the
DictVectorizer saved alongside the trained model.
"""
from __future__ import annotations

import ast
import re

import numpy as np

_DEFAULTDICT_RE = re.compile(r".*defaultdict\(<class 'int'>, (.*)\)")


def parse_dict(text) -> dict:
    if not isinstance(text, str):
        return {}
    m = _DEFAULTDICT_RE.match(text)
    s = m.group(1) if m else text
    try:
        return ast.literal_eval(s)
    except (ValueError, SyntaxError):
        return {}


def featurize(smiles: str):  # no live compute
    return None


def decode(text: str) -> dict | None:
    if not text:
        return None
    d = parse_dict(text)
    return d if d else None


def vectorize(feature, vectorizer) -> np.ndarray:
    if vectorizer is None:
        # Fall back: hash keys into a fixed-width dense vector (rare path; only
        # if a vectorizer wasn't saved). Keeps predict from crashing.
        vec = np.zeros(512, dtype=float)
        for k, v in feature.items():
            vec[hash(k) % 512] += float(v)
        return vec
    return np.asarray(vectorizer.transform([feature])[0], dtype=float)
