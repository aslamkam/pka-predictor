"""Disk cache for predictions.

One JSON file per (canonical SMILES, model id, temperature point). Stores the
full input feature vector(s) and all outputs so a repeat call is a no-op and the
inputs are inspectable later. Embedding extraction (UMA) is cached separately on
disk by InChIKey (.npy); a temperature sweep simply loops single-point cache keys.
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any

from .config import PREDICTION_CACHE_DIR


def make_key(canon_smiles: str, model_id: str, t_kelvin: float) -> str:
    raw = f"{canon_smiles}|{model_id}|{round(float(t_kelvin), 3)}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def _path(key: str) -> Path:
    return PREDICTION_CACHE_DIR / f"{key}.json"


def cache_get(key: str) -> dict[str, Any] | None:
    p = _path(key)
    if p.exists():
        try:
            return json.loads(p.read_text())
        except (json.JSONDecodeError, OSError):
            return None
    return None


def cache_put(key: str, record: dict[str, Any]) -> None:
    rec = dict(record)
    rec.setdefault("cached_at", time.strftime("%Y-%m-%d %H:%M:%S"))
    try:
        _path(key).write_text(json.dumps(rec, indent=2, default=str))
    except OSError:
        pass


def cache_record(canon_smiles: str, model_id: str, t_kelvin: float,
                 inputs: dict, outputs: dict, notes: str = "") -> dict[str, Any]:
    """Build + persist a full record (inputs + outputs)."""
    rec = {
        "canonical_smiles": canon_smiles,
        "model_id": model_id,
        "t_kelvin": round(float(t_kelvin), 3),
        "inputs": inputs,
        "outputs": outputs,
        "notes": notes,
    }
    cache_put(make_key(canon_smiles, model_id, t_kelvin), rec)
    return rec
