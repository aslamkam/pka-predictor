#!/usr/bin/env python3
"""Gradio web GUI for the pKa predictor.

  python app.py            # serves on http://localhost:7860
  python cli.py gui        # same thing, via the CLI
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
os.environ.setdefault("PKA_APP_ROOT", str(HERE))

import gradio as gr  # noqa: E402

from pkapredict import config, core  # noqa: E402

# (id, label) choices for the model chooser, grouped for readability.
_STD_CHOICES = [(e["label"], e["id"]) for e in core.list_models(family="standard")]
_UMA_CHOICES = [(e["label"], e["id"]) for e in core.list_models(family="uma")]
_ALL_CHOICES = _STD_CHOICES + _UMA_CHOICES
_FEATSETS = config.STANDARD_FEATURESETS


def _to_kelvin(temp, unit):
    try:
        t = float(temp)
    except (TypeError, ValueError):
        t = config.DEFAULT_T_K
    return t if (unit or "K").upper() == "K" else t + config.T0_K


def _row_for(mid: str, rec: dict) -> dict:
    """Flatten one model's record into a table row."""
    row = {k: None for k in ("model", "chembl_pred", "computed_pred", "pasted_pred",
                             "pKaH1", "pKaH2", "pKaH3", "dH_kJmol", "cx_pKa", "notes")}
    row["model"] = mid
    if "error" in rec:
        row["notes"] = f"ERROR: {rec['error']}"
        return row
    if rec.get("family") == "uma" or mid.startswith("uma-"):
        row["pKaH1"] = rec.get("pKaH1"); row["pKaH2"] = rec.get("pKaH2")
        row["pKaH3"] = rec.get("pKaH3"); row["dH_kJmol"] = rec.get("dH_25C_kJmol")
        row["notes"] = (f"levels={rec.get('levels_available')}; "
                        f"{rec.get('thermo_error','')}" if rec.get("thermo_error")
                        else f"levels={rec.get('levels_available')}; head={rec.get('head')}")
    else:
        row["chembl_pred"] = rec.get("chembl_pred")
        row["computed_pred"] = rec.get("computed_pred")
        row["pasted_pred"] = rec.get("pasted_pred")
        row["cx_pKa"] = rec.get("cx_pka")
        row["notes"] = rec.get("feature_notes", "")
    return row


COLS = ["model", "chembl_pred", "computed_pred", "pasted_pred",
        "pKaH1", "pKaH2", "pKaH3", "dH_kJmol", "cx_pKa", "notes"]
# Per-column Gradio datatype: "str" for text, "number" for numerics (so they
# format as values, not "[object Object]"). Must line up with COLS.
COL_TYPES = ["str", "number", "number", "number", "number", "number",
             "number", "number", "number", "str"]
_NUMERIC_COLS = {"chembl_pred", "computed_pred", "pasted_pred",
                 "pKaH1", "pKaH2", "pKaH3", "dH_kJmol", "cx_pKa"}

# Temperature-sweep results table: one row per grid point.
SWEEP_COLS = ["temperature", "unit", "pKaH1", "pKaH2", "pKaH3"]
SWEEP_TYPES = ["number", "str", "number", "number", "number"]


def _rows_to_list(rows: list[dict], cols: list[str]) -> list[list]:
    """Flatten list-of-dicts into list-of-lists ordered by `cols`.

    Gradio's Dataframe treats a dict cell as an opaque JS object (rendered as
    "[object Object]"). Returning list-of-lists with a matching `datatype` makes
    each cell a primitive the frontend can display. None stays None (blank cell).
    """
    return [[r.get(c) for c in cols] for r in rows]


def on_predict(smiles, models, temp, unit, paste_featset, paste_text, max_levels):
    if not smiles or not models:
        return [], "Enter a SMILES and select at least one model."
    pasted = {paste_featset: paste_text} if (paste_featset and paste_text) else None
    t_k = _to_kelvin(temp, unit)
    results = core.predict(smiles, list(models), t_kelvin=t_k,
                           pasted_vectors=pasted, max_levels=int(max_levels or 3))
    rows = [_row_for(mid, rec) for mid, rec in results.items()]
    n_cached = sum(1 for r in results.values() if r.get("from_cache"))
    status = (f"Predicted {len(results)} model(s) at {t_k:.2f} K "
              f"({n_cached} from cache). Full records saved under "
              f"{config.PREDICTION_CACHE_DIR}.")
    return _rows_to_list(rows, COLS), status


def _sweep_rows(curves: dict, ts_kelvin: list[float], unit: str) -> list[dict]:
    """Build a display row per temperature point from the sweep curves.

    curves: {level: [(t_kelvin, pKa), ...]} from core.sweep_temperature.
    Rows are ordered by temperature; missing levels are blank (not NaN).
    """
    # Index each level's curve by its temperature so we can join by point.
    by_level = {k: {round(t, 3): pk for t, pk in pts} for k, pts in curves.items()}
    rows = []
    for t_k in ts_kelvin:
        t_disp = round(t_k, 2) if unit.upper() == "K" else round(t_k - config.T0_K, 2)
        row = {"temperature": t_disp, "unit": unit.upper()}
        for k in (1, 2, 3):
            v = by_level.get(k, {}).get(round(t_k, 3))
            row[f"pKaH{k}"] = None if v is None else round(float(v), 3)
        rows.append(row)
    return rows


def on_plot(smiles, head_model, n_points, step, unit, t0, max_levels):
    if not smiles or not head_model:
        return None, [], "Enter a SMILES and pick a UMA model."
    if head_model.startswith("uma-"):
        head = head_model[len("uma-"):]
    else:
        head = head_model
    unit = (unit or "C").upper()
    t0_k = _to_kelvin(t0 if t0 is not None else (0.0 if unit == "C" else 273.15), unit)
    ts = [t0_k + i * float(step or 10.0) for i in range(max(2, int(n_points or 10)))]
    try:
        res = core.sweep_temperature(smiles, head, ts, unit=unit,
                                     max_levels=int(max_levels or 3))
    except Exception as ex:  # noqa: BLE001
        msg = str(ex)
        # uma-s-1p2 (facebook/UMA) is gated; a calculator-init failure is almost
        # always a missing/invalid HuggingFace token. Match either the wrapped
        # message or the underlying HF error text.
        looks_gated = any(s in msg.lower() for s in
                          ("restricted", "authenticated", "access token",
                           "401", "gated", "calculator failed to initialise",
                           "failed to initialize"))
        hint = ""
        if looks_gated:
            hint = (" — this is the gated facebook/UMA model. Put a HuggingFace "
                    "token in pka_app/.hf_token (or set the HF_TOKEN env var) "
                    "and restart the app. See README > HuggingFace token.")
        return None, [], f"❌ UMA sweep failed: {msg}{hint}"
    # Show both figures in one gallery (captioned), plus the numeric sweep table.
    gallery = [(res["pka_vs_T"], "pKa vs Temperature"),
               (res["vant_hoff"], "van't Hoff (ln K_a vs 1/T)")]
    rows = _rows_to_list(_sweep_rows(res["curves"], ts, unit), SWEEP_COLS)
    n_levels = sum(1 for k in (1, 2, 3) if res["curves"].get(k))
    if n_levels == 0:
        return None, [], (f"❌ Swept {len(ts)} points but no protonation levels could "
                          f"be predicted (UMA could not initialize — check the "
                          f"HuggingFace token for facebook/UMA).")
    status = (f"Swept {len(ts)} points ({res['n_cached_points']} from cache); "
              f"{n_levels} protonation level(s) predicted. "
              f"Figures + table shown below.")
    return gallery, rows, status


def build_ui():
    with gr.Blocks(title="pKa Predictor") as ui:
        gr.Markdown("## pKa Predictor\nPredict pKa from a SMILES with the standard "
                    "ML models or the FairChem **UMA** Basicity model. "
                    "Inputs + outputs are cached to disk.")
        with gr.Row():
            with gr.Column(scale=3):
                smiles = gr.Textbox(label="SMILES", value="C1CCCN1")
                examples = gr.Examples(examples=[["C1CCCN1"], ["C1CNCCN1"], ["NCCN"],
                                                 ["NC(CO)CO"], ["CN1CCOC(c2ccccc2)C1"]],
                                       inputs=[smiles])
            with gr.Column(scale=2):
                temp = gr.Number(label="Temperature", value=config.DEFAULT_T_K)
                unit = gr.Radio(["K", "C"], value="K", label="Unit")
        models = gr.CheckboxGroup(choices=_ALL_CHOICES, label="Models (pick any)",
                                  value=["std-12C-Morgan-Fingerprints-RF"])
        with gr.Accordion("Optional: paste a precomputed feature vector "
                          "(Benson/Maginn/or to override)", open=False):
            with gr.Row():
                paste_featset = gr.Dropdown(_FEATSETS, value="Benson-Groups",
                                            label="Feature set")
                paste_text = gr.Textbox(label="Feature vector / dict", lines=2,
                                        placeholder="e.g. defaultdict(..., {'N3s-...': 1}) "
                                        "or 0.13,0.02,...")
        btn = gr.Button("Predict", variant="primary")
        table = gr.Dataframe(headers=COLS, datatype=COL_TYPES,
                             interactive=False, wrap=True)
        status = gr.Markdown()
        btn.click(on_predict,
                  inputs=[smiles, models, temp, unit, paste_featset, paste_text,
                          gr.Number(value=3, visible=False, label="max_levels")],
                  outputs=[table, status])

        gr.Markdown("---\n### UMA temperature sweep (pKa vs T + van't Hoff)")
        with gr.Row():
            head = gr.Dropdown(_UMA_CHOICES, value="uma-invt", label="UMA model")
            n_points = gr.Number(value=10, label="# temperature points")
            step = gr.Number(value=10, label="step")
            punit = gr.Radio(["C", "K"], value="C", label="unit")
            t0 = gr.Number(value=0, label="start T")
        pbtn = gr.Button("Plot sweep")
        gallery = gr.Gallery(label="pKa vs Temperature   |   van't Hoff (ln K_a vs 1/T)",
                             columns=2, height=420, show_label=True)
        sweep_table = gr.Dataframe(headers=SWEEP_COLS, datatype=SWEEP_TYPES,
                                   interactive=False, wrap=True,
                                   label="Predicted pKa at each temperature")
        pstatus = gr.Markdown()
        pbtn.click(on_plot, inputs=[smiles, head, n_points, step, punit, t0,
                                    gr.Number(value=3, visible=False)],
                   outputs=[gallery, sweep_table, pstatus])
        gr.Markdown(f"_Cache: `{config.CACHE_DIR}_  |  Orca-Sigma excluded; "
                    "Benson/Maginn via ChEMBL lookup or pasted vector; "
                    "standard models are CPU-default retrained artifacts._")
    return ui


def launch(server_port: int = 7860, share: bool = False):
    ui = build_ui()
    # Gradio only serves files to the browser if they live under the working dir,
    # /tmp, or an explicitly allow-listed path. The sweep figures are written to
    # the mounted cache volume (PKA_CACHE_DIR=/cache -> /cache/plots), so without
    # this the whole response (table included) is dropped with InvalidPathError.
    allowed = [str(config.PLOTS_DIR), str(config.CACHE_DIR)]
    ui.launch(server_name="0.0.0.0", server_port=server_port, share=share,
              show_error=True, allowed_paths=allowed)


if __name__ == "__main__":
    launch()
