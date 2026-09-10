"""High-level predict() orchestrator: SMILES + chosen models + temperature ->
results dict, with disk caching of inputs + outputs.

Standard models report three pKa numbers side-by-side:
  - chembl_pred   : prediction from the SMILES's STORED ChEMBL feature row (if the
                    SMILES is in the dataset)
  - computed_pred : prediction from features WE compute from the SMILES (Morgan /
                    Joback via RDKit+SMARTS; None for Maginn)
  - pasted_pred   : prediction from a user-supplied precomputed feature vector
plus the experimental CX Basic pKa label when known.

UMA models report pKaH1/H2/H3 (+ ΔH°, ΔCp° for the 1/T heads) at the chosen T.
"""
from __future__ import annotations

import hashlib
from typing import Any

from . import cache, config, smiles_util as su
from .featurizers import registry as featreg


def _model_info(model_id: str) -> dict:
    e = config.REGISTRY_BY_ID.get(model_id)
    if e is None:
        raise KeyError(f"unknown model id {model_id!r}")
    return e


def list_models(family: str | None = None) -> list[dict]:
    if family is None:
        return list(config.REGISTRY)
    return [e for e in config.REGISTRY if e["family"] == family]


def _standard_predict(model_id: str, canon: str, pasted_text: str | None) -> dict:
    from . import standard_models as sm
    e = _model_info(model_id)
    fs, ds, algo = e["featureset"], e["dataset"], e["algo"]
    model = sm.get_model(model_id)
    if not model.exists():
        return {"model_id": model_id, "family": "standard", "error":
                f"no trained artifact (run train_standard_models.py for {ds}/{fs}/{algo})"}

    lookup = featreg.lookup(ds, fs, canon)
    computed_raw = featreg.featurize(fs, canon)
    pasted_raw = featreg.decode(fs, pasted_text) if pasted_text else None

    chembl_pred = model.predict_raw(lookup["raw"]) if lookup else None
    computed_pred = model.predict_raw(computed_raw) if computed_raw is not None else None
    pasted_pred = model.predict_raw(pasted_raw) if pasted_raw is not None else None

    notes = []
    if lookup: notes.append(f"ChEMBL row matched by {lookup['matched_by']}")
    if computed_raw is not None: notes.append("live compute (RDKit/SMARTS)")
    elif fs == "Maginn-Sigma-Profile":
        notes.append("no live compute (needs a GCN); use ChEMBL lookup or paste")
    if pasted_raw is not None: notes.append("pasted vector")
    return {
        "model_id": model_id, "family": "standard", "dataset": ds,
        "featureset": fs, "algo": algo,
        "chembl_pred": chembl_pred, "computed_pred": computed_pred,
        "pasted_pred": pasted_pred,
        "cx_pka": (lookup["cx_pka"] if lookup else None),
        "feature_notes": "; ".join(notes) or "no feature source available",
    }


def _predict_one(model_id: str, canon: str, t_kelvin: float,
                 pasted_text: str | None, max_levels: int, use_cache: bool) -> dict:
    e = _model_info(model_id)
    salt = ""
    if e["family"] == "standard" and pasted_text:
        salt = "||paste=" + hashlib.sha1(pasted_text.encode()).hexdigest()[:8]
    key = cache.make_key(canon + salt, model_id, t_kelvin)
    if use_cache:
        rec = cache.cache_get(key)
        if rec is not None:
            out = dict(rec.get("outputs", {}))
            out["from_cache"] = True
            return out
    if e["family"] == "uma":
        from .uma import predict as uma_predict
        out = uma_predict.predict_uma(e["head"], canon, t_kelvin, max_levels=max_levels)
    else:
        out = _standard_predict(model_id, canon, pasted_text)
    out.setdefault("model_id", model_id)
    out["from_cache"] = False
    if use_cache and "error" not in out:
        inputs = {"canonical_smiles": canon, "t_kelvin": round(float(t_kelvin), 2),
                  "model_id": model_id}
        if e["family"] == "standard":
            inputs["featureset"] = e["featureset"]
            if pasted_text:
                inputs["pasted_vector"] = pasted_text
        cache.cache_record(canon + salt, model_id, t_kelvin, inputs=inputs,
                           outputs=out, notes=out.get("feature_notes", ""))
    return out


def predict(smiles: str, model_ids: list[str], t_kelvin: float = 298.15,
           pasted_vectors: dict[str, str] | None = None, max_levels: int = 3,
           use_cache: bool = True) -> dict[str, Any]:
    """Predict for a SMILES across the chosen models. Returns {model_id: record}."""
    canon = su.canonicalize(smiles)
    if canon is None:
        return {mid: {"model_id": mid, "error": f"could not parse SMILES {smiles!r}"}
                for mid in model_ids}
    pasted_vectors = pasted_vectors or {}
    results: dict[str, Any] = {}
    for mid in model_ids:
        try:
            e = _model_info(mid)
            pasted = pasted_vectors.get(e.get("featureset")) if e["family"] == "standard" else None
            results[mid] = _predict_one(mid, canon, t_kelvin, pasted, max_levels, use_cache)
        except Exception as ex:  # noqa: BLE001
            results[mid] = {"model_id": mid, "error": str(ex)}
    return results


def sweep_temperature(smiles: str, head: str, t_kelvin_list: list[float],
                      max_levels: int = 3, unit: str = "K", out_dir=None):
    """Convenience: sweep + render the two figures for one UMA head."""
    from . import plotting
    canon = su.canonicalize(smiles) or smiles
    swept, n_cached = plotting.sweep_predictions(head, canon, t_kelvin_list, max_levels)
    p1, p2 = plotting.plot_figures(swept, unit=unit,
                                   title=f"{smiles}  (UMA {head})", out_dir=out_dir)
    return {"curves": {k: v for k, v in swept.items()}, "n_cached_points": n_cached,
            "pka_vs_T": str(p1), "vant_hoff": str(p2)}
