"""ChEMBL feature lookup — find a SMILES in the dataset's feature CSV and return
its stored raw feature vector + the CX Basic pKa label. Used for the
"ChEMBL-dataset prediction" column shown side-by-side with our computed one.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from .. import config
from ..smiles_util import canonicalize
from . import morgan, joback, benson, maginn

# Module-level cache of loaded lookup tables: (dataset, featureset) -> DataFrame.
_TABLES: dict[tuple[str, str], pd.DataFrame] = {}


def _master_csv(dataset: str) -> Path:
    return config.FEATURES_DIR / f"Chembl35_{dataset}_CX_Basic_pKa" / f"chembl35_{dataset}_amines.csv"


def _build_table(dataset: str, featureset: str) -> pd.DataFrame:
    # dtype=str avoids pandas inferring the 2048-digit Morgan bitstring (or the
    # encoded group/sigma columns) as a giant int -> OverflowError. Column ops
    # (not iterrows) keep this fast over thousands of rows.
    master = pd.read_csv(_master_csv(dataset), dtype=str)
    master = master.rename(columns={"CX Basic pKa": "cx_pka"})
    feat_csv = config.standard_feature_csv(dataset, featureset)
    rows: list[dict[str, Any]] = []
    if featureset == "Morgan-Fingerprints":
        df = pd.read_csv(feat_csv, dtype=str)
        fps = df.get("Morgan_Fingerprint", pd.Series(dtype=str)).fillna("").astype(str).tolist()
        raws = [morgan.decode(f) for f in fps]
        sm = df.get("Smiles").tolist(); ik = df.get("Standard Inchi Key").tolist()
        cx = df.get("CX Basic pKa").tolist(); cid = df.get("ChEMBL ID").tolist()
        for i, r in enumerate(raws):
            if r is not None:
                rows.append(dict(smiles=sm[i], inchikey=ik[i], cx_pka=cx[i],
                                 chembl_id=cid[i], raw=r))
    elif featureset == "Joback-Reid-Groups":
        df = pd.read_csv(feat_csv, dtype=str)
        merged = master.merge(df, left_on="ChEMBL ID", right_on="id", how="inner")
        cols = joback.COLUMNS
        present = [c for c in cols if c in merged.columns]
        counts = (merged[present].apply(pd.to_numeric, errors="coerce")
                  .fillna(0.0).to_numpy(dtype=float))
        sm = merged["Smiles"].tolist(); ik = merged["Standard Inchi Key"].tolist()
        cx = merged["cx_pka"].tolist(); cid = merged["ChEMBL ID"].tolist()
        for i in range(len(merged)):
            rows.append(dict(smiles=sm[i], inchikey=ik[i], cx_pka=cx[i],
                             chembl_id=cid[i], raw=counts[i]))
    elif featureset == "Benson-Groups":
        df = pd.read_csv(feat_csv, dtype=str)
        merged = master.merge(df[["Smiles", "benson_groups"]], on="Smiles", how="inner")
        sm = merged["Smiles"].tolist(); ik = merged["Standard Inchi Key"].tolist()
        cx = merged["cx_pka"].tolist(); cid = merged["ChEMBL ID"].tolist()
        bg = merged["benson_groups"].fillna("").astype(str).tolist()
        for i, txt in enumerate(bg):
            d = benson.parse_dict(txt)
            if d:
                rows.append(dict(smiles=sm[i], inchikey=ik[i], cx_pka=cx[i],
                                 chembl_id=cid[i], raw=d))
    elif featureset == "Maginn-Sigma-Profile":
        df = pd.read_csv(feat_csv, dtype=str)
        sp = df.get("El_Sigma_Profile", pd.Series(dtype=str)).fillna("").astype(str).tolist()
        sm = df.get("Smiles").tolist(); ik = df.get("Standard Inchi Key").tolist()
        cx = df.get("CX Basic pKa").tolist(); cid = df.get("ChEMBL ID").tolist()
        for i, txt in enumerate(sp):
            raw = maginn.parse_array(txt)
            if raw is not None and raw.size:
                rows.append(dict(smiles=sm[i], inchikey=ik[i], cx_pka=cx[i],
                                 chembl_id=cid[i], raw=raw))
    else:
        return pd.DataFrame()

    tbl = pd.DataFrame(rows)
    if not tbl.empty:
        tbl["smiles_canon"] = tbl["smiles"].astype(str).map(lambda s: canonicalize(s) or s)
    return tbl


def np_safe(cols, row):
    import numpy as np
    return np.asarray([float(row[c]) if pd.notna(row[c]) else 0.0 for c in cols], dtype=float)


def get_table(dataset: str, featureset: str) -> pd.DataFrame:
    key = (dataset, featureset)
    if key not in _TABLES:
        _TABLES[key] = _build_table(dataset, featureset)
    return _TABLES[key]


def lookup(dataset: str, featureset: str, smiles: str) -> dict[str, Any] | None:
    """Match by canonical SMILES, then InChIKey. Returns raw feature + metadata."""
    tbl = get_table(dataset, featureset)
    if tbl is None or tbl.empty:
        return None
    canon = canonicalize(smiles)
    ik = None
    if canon:
        hit = tbl[tbl["smiles_canon"] == canon]
        if not hit.empty:
            r = hit.iloc[0]
            return _pack(r, "canonical SMILES")
    # InChIKey fallback
    try:
        from rdkit import Chem
        m = Chem.MolFromSmiles(smiles)
        if m is not None:
            ik = Chem.MolToInchiKey(m)
    except Exception:
        ik = None
    if ik and "inchikey" in tbl.columns:
        hit = tbl[tbl["inchikey"].astype(str) == ik]
        if not hit.empty:
            r = hit.iloc[0]
            return _pack(r, "InChIKey")
    return None


def _pack(row, matched_by) -> dict[str, Any]:
    return {
        "raw": row["raw"],
        "cx_pka": float(row["cx_pka"]) if pd.notna(row.get("cx_pka")) else None,
        "smiles": row.get("smiles"),
        "inchikey": row.get("inchikey"),
        "chembl_id": row.get("chembl_id"),
        "matched_by": matched_by,
    }
