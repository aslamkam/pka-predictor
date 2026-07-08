"""SMILES utilities: canonicalization, InChIKey, neutralization, and a
protonation-state enumerator that generates the H1/H2/H3 forms of an amine.

The protonation convention (verified against the pKahub training data): a pKaH_k
row pairs the (k-1)-protonated form as "base" with the k-protonated form as
"protonated". So to predict pKaH1/H2/H3 we need embeddings of forms 0..3
(neutral, BH+, BH2++, BH3+++). This module yields that ladder by protonating the
most-basic nitrogen at each step (RDKit heuristic; best for the aliphatic
amine / diamine / amino-alcohol CCUS domain).
"""
from __future__ import annotations

from typing import List, Tuple

from rdkit import Chem
from rdkit.Chem import AllChem, DataStructs  # noqa: F401  (Morgan featurizer uses these)


def mol_from_smiles(smiles: str):
    return Chem.MolFromSmiles(smiles)


def canonicalize(smiles: str) -> str | None:
    m = mol_from_smiles(smiles)
    if m is None:
        return None
    return Chem.MolToSmiles(m)


def inchikey(smiles: str) -> str | None:
    m = mol_from_smiles(smiles)
    if m is None:
        return None
    try:
        return Chem.MolToInchiKey(m)
    except Exception:
        return None


def neutralize(smiles: str) -> str | None:
    """Return a neutralized, desalted canonical SMILES (Uncharger)."""
    m = mol_from_smiles(smiles)
    if m is None:
        return None
    try:
        from rdkit.Chem.MolStandardize import rdMolStandardize
        uc = rdMolStandardize.Uncharger()
        m = uc.uncharge(m)
    except Exception:
        pass
    # Keep the largest fragment (drop salts).
    frags = Chem.GetMolFrags(m, asMols=True, sanitizeFrags=False)
    if len(frags) > 1:
        m = max(frags, key=lambda f: f.GetNumAtoms())
    try:
        Chem.SanitizeMol(m)
    except Exception:
        pass
    return Chem.MolToSmiles(m)


# Amide N (C(=O)-N, S(=O)2-N, P(=O)-N) — NOT basic; skip these.
_AMIDE_N = Chem.MolFromSmarts("[N;$(NC=O),$(NS(=O)=O),$(NP=O)]")
# Candidate basic nitrogens: uncharged N with a lone pair, excluding amide N.
_BASIC_N = Chem.MolFromSmarts(
    "[#7;!$([n]);!$([N+]);!$([N;$(NC=O),$(NS(=O)=O),$(NP=O)])]"
)
_AROMATIC_N = Chem.MolFromSmarts("[n]")


def _basicity_score(mol, atom) -> float:
    """Higher = more basic. Approximates proton affinity for amines."""
    idx = atom.GetIdx()
    # Aromatic ring N (pyridine etc.) is far less basic than sp3 alkyl N.
    aromatic = mol.GetAtomWithIdx(idx).GetIsAromatic()
    n_neighbors = len([a for a in atom.GetNeighbors() if a.GetSymbol() != "H"])
    # Alkyl substitution boosts basicity (inductive donation): 3° > 2° > 1°.
    carbon_neighbors = len([a for a in atom.GetNeighbors() if a.GetSymbol() == "C"])
    score = 10.0 * carbon_neighbors + 3.0 * (n_neighbors - 1)
    if aromatic:
        score -= 6.0
    # In-ring sp3 N (piperidine / piperazine) is strongly basic.
    if atom.IsInRing() and not aromatic:
        score += 4.0
    return score


def _candidate_sites(mol) -> list[int]:
    """Indices of basic N atoms worth protonating, highest basicity first."""
    amide = set()
    if _AMIDE_N is not None:
        amide = {tup[0] for tup in mol.GetSubstructMatches(_AMIDE_N)}
    sites = []
    for atom in mol.GetAtoms():
        if atom.GetSymbol() != "N":
            continue
        if atom.GetFormalCharge() > 0:
            continue
        if atom.GetIdx() in amide:
            continue
        sites.append(atom.GetIdx())
    sites.sort(key=lambda i: _basicity_score(mol, mol.GetAtomWithIdx(i)), reverse=True)
    return sites


def _protonate_atom(mol, idx: int):
    """Return a new mol with atom `idx` protonated (formal charge +1)."""
    emol = Chem.RWMol(mol)
    a = emol.GetAtomWithIdx(idx)
    a.SetFormalCharge(a.GetFormalCharge() + 1)
    try:
        emol.UpdatePropertyCache(strict=False)
        Chem.SanitizeMol(emol)
    except Exception:
        # Sanitization can fail for exotic valences; the charge edit still applies.
        pass
    return emol.GetMol()


def enumerate_protonations(base_smiles: str, max_levels: int = 3
                           ) -> List[Tuple[int, str]]:
    """Return [(level, protonated_smiles), ...] for levels 1..max_levels.

    Each `level` SMILES is the form protonated `level` times (H1 => BH+, etc.).
    Stops early when no further basic N is available. The returned SMILES are
    canonical; None entries are omitted.
    """
    neutral = canonicalize(neutralize(base_smiles) or base_smiles)
    if neutral is None:
        return []
    out: List[Tuple[int, str]] = []
    cur_smiles = neutral
    for level in range(1, max_levels + 1):
        m = mol_from_smiles(cur_smiles)
        if m is None:
            break
        sites = _candidate_sites(m)
        if not sites:
            break
        pm = _protonate_atom(m, sites[0])
        ps = Chem.MolToSmiles(pm)
        if ps is None or ps == cur_smiles:
            break
        out.append((level, ps))
        cur_smiles = ps
    return out


def protonation_ladder(base_smiles: str, max_levels: int = 3
                       ) -> List[Tuple[int, str, str]]:
    """Return [(level, base_form_smiles, protonated_form_smiles), ...] for the
    pKaH_k feature pairing: level k pairs form (k-1) as base with form k as prot.
    """
    neutral = canonicalize(neutralize(base_smiles) or base_smiles)
    if neutral is None:
        return []
    forms = [neutral] + [ps for _, ps in enumerate_protonations(neutral, max_levels)]
    ladder: List[Tuple[int, str, str]] = []
    for k in range(1, min(len(forms), max_levels + 1)):
        ladder.append((k, forms[k - 1], forms[k]))
    return ladder


def morgan_bits(smiles: str, n_bits: int = 2048, radius: int = 2):
    """2048-bit radius-2 Morgan fingerprint as a numpy int vector (matches the
    ChEMBL feature CSV's Morgan_Fingerprint bit-string column)."""
    import numpy as np
    m = mol_from_smiles(smiles)
    if m is None:
        return None
    bv = AllChem.GetMorganFingerprintAsBitVect(m, radius, nBits=n_bits)
    arr = np.zeros((n_bits,), dtype=float)
    DataStructs.ConvertToNumpyArray(bv, arr)
    return arr
