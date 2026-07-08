"""Morgan fingerprints (2048 bits, radius 2) — matches the ChEMBL feature CSV."""
from __future__ import annotations

import ast
import numpy as np

from ..smiles_util import morgan_bits

N_BITS = 2048
RADIUS = 2


def featurize(smiles: str) -> np.ndarray | None:
    return morgan_bits(smiles, N_BITS, RADIUS)


def decode(text: str) -> np.ndarray | None:
    """Accept a bitstring ('0101...'), a comma/sep list, or a Python list repr."""
    if not text:
        return None
    s = text.strip()
    try:
        if s.startswith("["):
            return np.asarray(ast.literal_eval(s), dtype=float)
        if "," in s:
            return np.asarray([float(x) for x in s.split(",")], dtype=float)
        # bare bitstring — vectorized (char-by-char int() over 2048 chars x
        # thousands of rows was the training bottleneck).
        arr = np.frombuffer(s.encode("ascii"), dtype=np.uint8).astype(np.float32)
        arr -= ord("0")
        return arr
    except Exception:
        return None


def vectorize(feature, vectorizer=None) -> np.ndarray:
    return np.asarray(feature, dtype=float)
