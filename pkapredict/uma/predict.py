"""Predict pKaH1/H2/H3 (+ ΔH°, ΔCp°) for one SMILES at one temperature with a
given UMA temperature-head ensemble.

Builds the 1158-D relaxed feature vector via data_relaxed.build_feature_matrix and
ensembles across the head's 3 leak-free split-seed run dirs (each a 5-seed
Stage-3 ensemble), exactly like uma_ccus_predict.py / plot_vant_hoff_figure.py.
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from .. import config, smiles_util as su
from . import _paths  # noqa: F401
from . import extract as _extract

# Late imports of thesis modules (on sys.path via _paths).
import data_relaxed        # noqa: E402
import infer               # noqa: E402
from engine import apply_scaler  # noqa: E402


_ENSEMBLES: dict[str, list] = {}      # head -> [(scaler, [PkaMLP,...]), ...]
_CACHE: dict = {}


def _embedding_cache():
    if "cache" not in _CACHE:
        _CACHE["cache"] = data_relaxed.EmbeddingCache(
            global_dir=config.EMB_GLOBAL_DIR, local_dir=config.EMB_LOCAL_DIR)
    # Refresh available set each call (new files may have been written).
    c = _CACHE["cache"]
    g = {p.stem for p in config.EMB_GLOBAL_DIR.glob("*.npy")}
    l = {p.stem for p in config.EMB_LOCAL_DIR.glob("*.npy")}
    c.available = g & l
    return c


def _load_head_ensembles(head: str):
    if head in _ENSEMBLES:
        return _ENSEMBLES[head]
    run_dirs = config.UMA_RUN_DIRS.get(head, [])
    if not run_dirs:
        raise FileNotFoundError(f"no UMA run dirs resolved for head={head!r} "
                                f"(expected under {config.BASICITY_DIR/'runs'})")
    ens = [infer.load_ensemble(rd) for rd in run_dirs]      # [(scaler, [models])]
    _ENSEMBLES[head] = ens
    return ens


def _build_X(base_key: str, prot_key: str, t_celsius: float):
    row = {"Inchi_Key": base_key, "Protonated_Inchi_Key": prot_key,
           "Temperature": float(t_celsius), "pKa": float("nan"),
           **config.WATER_SOLVENT}
    df = pd.DataFrame([row])
    cache = _embedding_cache()
    X, _y, _w = data_relaxed.build_feature_matrix(df, cache)
    return X


def _read_thermo(ens, base_key: str, prot_key: str) -> dict[str, float | None]:
    """Direct ΔH° (and ΔCp° for invtlnt) read-off from the head's B (and C)
    outputs at 25 °C, replicating plot_vant_hoff_figure.model_sweep."""
    try:
        import torch
        scaler, models = ens[0]
        Xr = _build_X(base_key, prot_key, 25.0)
        Xr_s = apply_scaler(scaler, Xr)
        xt = torch.from_numpy(np.ascontiguousarray(Xr_s))
        with torch.no_grad():
            outs = [m.net(xt)[0] for m in models]
        cfg = models[0].cfg
        head = getattr(cfg, "temp_head", "none")
        sigma_invT = float(cfg.sigma_invT)
        Bm = float(np.mean([float(o[1]) for o in outs]))
        dH = Bm * config.R_GAS * config.LN10 / sigma_invT / 1000.0    # kJ/mol
        dCp = None
        if head == "invtlnt":
            sigma_lnT = float(cfg.sigma_lnT)
            Cm = float(np.mean([float(o[2]) for o in outs]))
            dCp = -config.R_GAS * config.LN10 * Cm / sigma_lnT        # J/(mol K)
            dH = (config.R_GAS * config.LN10
                  * (Bm / sigma_invT - 298.15 * Cm / sigma_lnT) / 1000.0)
        if head in ("none", "linear"):
            return {}      # no direct enthalpy output for these heads
        return {"dH_25C_kJmol": round(dH, 2),
                "dCp_JmolK": (None if dCp is None else round(dCp, 1))}
    except Exception as e:  # noqa: BLE001
        return {"thermo_error": str(e)}


def predict_uma(head: str, base_smiles: str, t_kelvin: float,
                max_levels: int = 3, n_conformers: int = 3,
                verbose: bool = True) -> dict[str, Any]:
    forms, level_pairs = _extract.prepare_ladder(base_smiles, max_levels)
    if not level_pairs:
        return {"error": "could not enumerate protonation states (parse/neutralize failed)"}
    _extract.ensure_embeddings(forms, n_conformers=n_conformers, verbose=verbose)
    cache = _embedding_cache()
    ens = _load_head_ensembles(head)
    t_c = float(t_kelvin) - config.T0_K

    out: dict[str, Any] = {
        "head": head, "t_kelvin": round(float(t_kelvin), 2),
        "neutral_smiles": su.canonicalize(base_smiles),
        "levels_available": 0,
    }
    per_level_preds = {}
    for k, bkey, pkey in level_pairs:
        if not (cache.has(bkey) and cache.has(pkey)):
            if verbose:
                print(f"  [uma] H{k}: missing embeddings ({bkey}/{pkey}) — skipping")
            continue
        X = _build_X(bkey, pkey, t_c)
        run_preds = [infer.predict_ensemble(scl, mds, X)[0] for scl, mds in ens]
        m = float(np.mean(run_preds))
        out[f"pKaH{k}"] = round(m, 3)
        out[f"pKaH{k}_std"] = round(float(np.std(run_preds)), 3)
        per_level_preds[k] = (bkey, pkey)
        out["levels_available"] += 1

    # Thermodynamic read-off from the H1 pair (the main macro-pKa).
    if 1 in per_level_preds:
        bkey, pkey = per_level_preds[1]
        out.update(_read_thermo(ens, bkey, pkey))
    return out
