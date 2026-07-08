"""Temperature-sweep plots for UMA pKaH1/H2/H3 — two figure types (thesis
Fig. 6.4 style):

  1. pKa vs Temperature            (x = T in the chosen unit; y = pKaH#)
  2. van't Hoff: ln K_a vs 1/T     (x = 1/T [K^-1]; y = -ln(10)·pKa)

All three pKaH curves are overlaid per figure. Per-point predictions are cached
via the standard cache, so a re-plot over the same grid is a cache hit.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from . import cache, config


def _cached_uma_point(head: str, canon_smiles: str, t_kelvin: float, max_levels: int):
    """Return cached pKaH dict for one (head, smiles, T), predicting+caching on miss.
    Keyed by the full model id (uma-<head>) so sweep points are shared with
    direct predict() calls at the same T."""
    model_id = f"uma-{head}"
    key = cache.make_key(canon_smiles, model_id, t_kelvin)
    rec = cache.cache_get(key)
    if rec is not None:
        return rec.get("outputs", {}), True
    from .uma import predict as uma_predict
    out = uma_predict.predict_uma(head, canon_smiles, t_kelvin, max_levels=max_levels,
                                  verbose=False)
    if "error" in out:
        return out, False
    cache.cache_record(canon_smiles, model_id, t_kelvin,
                       inputs={"source": "uma_relaxed_1158D", "head": head},
                       outputs=out, notes="uma sweep point")
    return out, False


def sweep_predictions(head: str, smiles: str, t_kelvin_list, max_levels: int = 3):
    """Return {level: list of (T_K, pKa)} for H1/H2/H3 across the grid (cached)."""
    out = {1: [], 2: [], 3: []}
    n_cached = 0
    for t in t_kelvin_list:
        res, was_cached = _cached_uma_point(head, smiles, t, max_levels)
        for k in (1, 2, 3):
            pk = res.get(f"pKaH{k}")
            if pk is not None:
                out[k].append((float(t), float(pk)))
        if was_cached:
            n_cached += 1
    return out, n_cached


def _unit_convert(t_kelvin: np.ndarray, unit: str) -> np.ndarray:
    return t_kelvin if unit.upper() == "K" else t_kelvin - config.T0_K


def plot_figures(swept: dict, unit: str = "K", title: str = "UMA pKa(T)",
                 out_dir: Path | None = None):
    """Render the two figures. Returns (path_pKa_vs_T, path_vant_hoff)."""
    out_dir = Path(out_dir or config.PLOTS_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)
    colors = {1: "tab:blue", 2: "tab:orange", 3: "tab:green"}

    # ---- Fig 1: pKa vs Temperature ----
    fig1, ax1 = plt.subplots(figsize=(6.5, 4.5))
    for k in (1, 2, 3):
        pts = swept.get(k, [])
        if not pts:
            continue
        tk = np.array([p[0] for p in pts])
        pk = np.array([p[1] for p in pts])
        ax1.plot(_unit_convert(tk, unit), pk, "-o", color=colors[k], lw=2, ms=5,
                 label=f"pKaH{k}")
    ax1.set_xlabel("temperature (K)" if unit.upper() == "K" else "temperature (°C)")
    ax1.set_ylabel("p$K_a$")
    ax1.set_title(title)
    ax1.grid(alpha=0.3)
    ax1.legend()
    fig1.tight_layout()
    p1 = out_dir / "pka_vs_T.png"
    fig1.savefig(p1, dpi=150)
    plt.close(fig1)

    # ---- Fig 2: van't Hoff (ln K_a vs 1/T) ----
    fig2, ax2 = plt.subplots(figsize=(6.5, 4.5))
    for k in (1, 2, 3):
        pts = swept.get(k, [])
        if not pts:
            continue
        tk = np.array([p[0] for p in pts])
        pk = np.array([p[1] for p in pts])
        inv_t = 1.0 / tk
        lnk = -config.LN10 * pk
        ax2.plot(inv_t, lnk, "-o", color=colors[k], lw=2, ms=5, label=f"pKaH{k}")
    ax2.set_xlabel(r"$1/T$  (K$^{-1}$)")
    ax2.set_ylabel(r"$\ln K_a = -\ln(10)\,\mathrm{p}K_a$")
    ax2.set_title(title + "  (van't Hoff)")
    ax2.grid(alpha=0.3)
    # Secondary top axis in °C for readability (like plot_vant_hoff_figure).
    try:
        sax = ax2.secondary_xaxis(
            "top",
            functions=(lambda x: 1.0 / np.where(x == 0, np.nan, x) - config.T0_K,
                       lambda tc: 1.0 / (np.asarray(tc) + config.T0_K)),
        )
        sax.set_xlabel("temperature (°C)")
    except Exception:
        pass
    ax2.legend()
    fig2.tight_layout()
    p2 = out_dir / "vant_hoff.png"
    fig2.savefig(p2, dpi=150)
    plt.close(fig2)
    return p1, p2
