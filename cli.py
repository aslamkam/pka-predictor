#!/usr/bin/env python3
"""pKa Predictor CLI.

  python cli.py list
  python cli.py predict --smiles "C1CCCN1" --models uma-invt,std-12C-Morgan-Fingerprints-RF --temp 298.15 --unit K
  python cli.py plot   --smiles "C1CCCN1" --model uma-invt --n 10 --step 10 --unit C --out plots
  python cli.py gui    # launch the Gradio app

Temperature defaults to Kelvin; --unit {K,C} selects the unit of --temp (and the
plot x-axis). Predictions + inputs are cached to the cache/ directory, so an
identical repeat call is a no-op.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
os.environ.setdefault("PKA_APP_ROOT", str(HERE))

from pkapredict import config, core  # noqa: E402


def _to_kelvin(temp: float, unit: str) -> float:
    unit = (unit or "K").upper()
    if unit == "K":
        return float(temp)
    if unit == "C":
        return float(temp) + config.T0_K
    raise ValueError(f"unknown unit {unit!r}")


def _parse_models(s: str) -> list[str]:
    return [m.strip() for m in s.split(",") if m.strip()]


def _parse_vectors(items: list[str]) -> dict[str, str]:
    """Each item is FEATSET=TEXT (TEXT may contain commas if quoted)."""
    out: dict[str, str] = {}
    for it in items or []:
        if "=" not in it:
            continue
        fs, text = it.split("=", 1)
        out[fs.strip()] = text
    return out


def cmd_list(args):
    for fam in ("standard", "uma"):
        print(f"\n=== {fam} ===")
        for e in core.list_models(family=fam):
            if fam == "standard":
                extra = f"[{e['dataset']}/{e['featureset']}/{e['algo']}]"
            else:
                extra = f"[head={e['head']}]"
            print(f"  {e['id']:46s} {extra}")


def cmd_predict(args):
    t_k = _to_kelvin(args.temp, args.unit)
    models = _parse_models(args.models)
    pasted = _parse_vectors(args.vector)
    res = core.predict(args.smiles, models, t_kelvin=t_k, pasted_vectors=pasted,
                       use_cache=not args.no_cache)
    print(json.dumps(res, indent=2, default=str))
    if not args.no_cache:
        print(f"\n(cached under {config.PREDICTION_CACHE_DIR})", file=sys.stderr)


def cmd_plot(args):
    if not args.model.startswith("uma-"):
        print("error: --model must be a uma-* model id", file=sys.stderr)
        sys.exit(2)
    head = args.model[len("uma-"):]
    unit = (args.unit or "K").upper()
    t0_k = _to_kelvin(args.t0, unit) if args.t0 is not None else _to_kelvin(0.0, unit)
    # Grid: n points spaced by `step` (in the chosen unit) starting at t0.
    ts = [t0_k + i * (_step_kelvin(args.step, unit)) for i in range(max(2, args.n))]
    res = core.sweep_temperature(args.smiles, head, ts, unit=unit,
                                 out_dir=args.out or None)
    print(json.dumps({"curves": {str(k): v for k, v in res["curves"].items()},
                      "n_cached_points": res["n_cached_points"],
                      "pka_vs_T": res["pka_vs_T"], "vant_hoff": res["vant_hoff"]},
                     indent=2))


def _step_kelvin(step: float, unit: str) -> float:
    return float(step) if unit.upper() == "K" else float(step)


def cmd_gui(args):
    from app import launch
    launch(server_port=args.port, share=args.share)


def main():
    ap = argparse.ArgumentParser(prog="pka-predict", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list", help="list available models").set_defaults(func=cmd_list)

    p = sub.add_parser("predict", help="predict pKa for a SMILES")
    p.add_argument("--smiles", required=True)
    p.add_argument("--models", required=True, help="comma-separated model ids")
    p.add_argument("--temp", type=float, default=298.15, help="temperature (default K)")
    p.add_argument("--unit", choices=["K", "C", "k", "c"], default="K")
    p.add_argument("--vector", action="append", help="FEATSET=pasted_feature_text (repeatable)")
    p.add_argument("--no-cache", action="store_true")
    p.set_defaults(func=cmd_predict)

    p = sub.add_parser("plot", help="UMA pKa(T) + van't Hoff plots")
    p.add_argument("--smiles", required=True)
    p.add_argument("--model", required=True, help="a uma-* model id")
    p.add_argument("--n", type=int, default=10, help="number of temperature points")
    p.add_argument("--step", type=float, default=10.0, help="interval between points (in --unit)")
    p.add_argument("--t0", type=float, default=None, help="start temperature (default 0 C / 273.15 K)")
    p.add_argument("--unit", choices=["K", "C", "k", "c"], default="C")
    p.add_argument("--out", default=None, help="output dir for PNGs")
    p.set_defaults(func=cmd_plot)

    p = sub.add_parser("gui", help="launch the Gradio web GUI")
    p.add_argument("--port", type=int, default=7860)
    p.add_argument("--share", action="store_true")
    p.set_defaults(func=cmd_gui)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
