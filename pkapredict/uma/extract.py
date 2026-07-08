"""Ensure vacuum-relaxed uma-s-1p2 embeddings exist on disk for a molecule's
base + H1/H2/H3 protonated forms, extracting any that are missing.

Localization convention (matches the pKahub pairing verified in smiles_util):
  - form 0 (neutral base)     -> proto_smiles = form 1
  - form k>=1 (k-protonated)  -> base_smiles  = form (k-1)
so get_relaxed_embeddings maps the newly-added proton to the right atom.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .. import config, smiles_util as su
from .calculator import get_calculator


def prepare_ladder(base_smiles: str, max_levels: int = 3):
    """Return (forms_to_embed, level_pairs).

    forms_to_embed: list of {smiles, key, proto_smiles, base_smiles} for forms 0..K.
    level_pairs:    list of (level, base_inchikey, prot_inchikey) for H1..HK.
    """
    ladder = su.protonation_ladder(base_smiles, max_levels)   # [(k, form(k-1) smi, form(k) smi)]
    if not ladder:
        return [], []
    neutral = ladder[0][1]
    forms_smi = [neutral] + [prot for (_, _, prot) in ladder]   # f0, f1, ..., fK

    forms: list[dict[str, Any]] = []
    for i, smi in enumerate(forms_smi):
        key = su.inchikey(smi)
        if i == 0:
            proto = forms_smi[1] if len(forms_smi) > 1 else None
            forms.append({"smiles": smi, "key": key, "proto_smiles": proto, "base_smiles": None})
        else:
            forms.append({"smiles": smi, "key": key, "proto_smiles": None,
                          "base_smiles": forms_smi[i - 1]})

    level_pairs = []
    for k, bsmi, psmi in ladder:
        level_pairs.append((k, su.inchikey(bsmi), su.inchikey(psmi)))
    return forms, level_pairs


def ensure_embeddings(forms: list[dict[str, Any]], n_conformers: int = 3,
                      verbose: bool = True) -> list[bool]:
    """Extract any missing embeddings. Returns per-form success bools."""
    pipe, calc, head = get_calculator()
    gdir = str(config.EMB_GLOBAL_DIR)
    ldir = str(config.EMB_LOCAL_DIR)
    # Make sure dirs exist (get_relaxed_embeddings also mkdirs).
    Path(gdir).mkdir(parents=True, exist_ok=True)
    Path(ldir).mkdir(parents=True, exist_ok=True)
    ok = []
    for f in forms:
        res = pipe.get_relaxed_embeddings(
            smiles=f["smiles"], inchi_key=f["key"],
            global_dir=gdir, local_dir=ldir,
            calculator=calc, head=head,
            proto_smiles=f.get("proto_smiles"),
            base_smiles=f.get("base_smiles"),
            n_conformers=n_conformers,
        )
        if verbose and not res:
            print(f"  [uma] embedding failed for {f['smiles']} ({f['key']})")
        ok.append(bool(res))
    return ok
