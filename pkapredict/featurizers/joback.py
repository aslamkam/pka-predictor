"""Joback-Reid group counts via a SMARTS table.

The ChEMBL feature CSV stores explicit per-group count columns; for an arbitrary
new SMILES we re-derive counts by SMARTS matching. The SMARTS below are a
best-effort reproduction of the group definitions (the original generator is not
in-repo); amine/alcohol/carbonyl/ring groups — the ones that matter for pKa — are
covered well, exotic carbon types less so. Use the ChEMBL lookup or a pasted
vector when an exact match to the training features is required.
"""
from __future__ import annotations

import ast
import numpy as np
from rdkit import Chem

# Column order MUST match the Joback CSV header exactly (see train loader).
COLUMNS = [
    "Acetylenic carbon (≡CH)", "Alcohol hydroxyl (–OH)", "Aldehyde carbonyl (–HC=O)",
    "Bromine (–Br)", "Carboxylic acid (–COOH)", "Chlorine (–Cl)", "Cumulated diene carbon (=C=)",
    "Ester carbonyl (–COO–)", "Ether oxygen (–O–)", "Fluorine (–F)", "Imine (>N=)",
    "Iminium (=NH)", "Internal acetylenic carbon (≡C–)", "Iodine (–I)", "Ketone carbonyl (>C=O)",
    "Methine carbon (–CH–)", "Methyl carbon (–CH₃)", "Methylene carbon (–CH₂–)",
    "Nitrile (–C≡N)", "Nitro (–NO₂)", "Nitroso oxygen (=O in –N=O)", "Olefinic quaternary carbon (=C<)",
    "Phenolic hydroxyl (–OH)", "Primary amine (–NH₂)", "Quaternary carbon (–C–)", "Ring =C<",
    "Ring =CH–", "Ring >C<", "Ring >CH–", "Ring ether oxygen (–O– ring)", "Ring imine (>N= ring)",
    "Ring ketone carbonyl (>C=O)", "Ring secondary amine (–NH– ring)", "Ring thioether sulfur (–S– ring)",
    "Ring –CH₂–", "Secondary amine (–NH–)", "Tertiary amine (>N–)", "Thioether sulfur (–S–)",
    "Thiol (–SH)", "Vinyl carbon (=CH–)", "Vinyl carbon (=CH₂)",
]

# (column, SMARTS). Counts are number of matches (use unique-atom matches).
SMARTS = {
    "Acetylenic carbon (≡CH)": "[CH1]#C",            # terminal alkyne C-H
    "Internal acetylenic carbon (≡C–)": "[CH0]#[CH0]",  # internal alkyne
    "Alcohol hydroxyl (–OH)": "[CX4][OX2H1]",          # aliphatic alcohol
    "Phenolic hydroxyl (–OH)": "[c][OX2H1]",           # aromatic C-OH
    "Aldehyde carbonyl (–HC=O)": "[CX3H1](=O)",        # aldehyde
    "Ketone carbonyl (>C=O)": "[CX3H0](=O)([#6])[#6]", # ketone (C=O bonded to 2 C)
    "Ring ketone carbonyl (>C=O)": "[CX3H0;R](=O)",    # ring ketone
    "Carboxylic acid (–COOH)": "[CX3](=O)[OX1H0][OX2H1]",  # -C(=O)OH (deprotonated-aware)
    "Ester carbonyl (–COO–)": "[CX3](=O)[OX2H0][#6]",  # -C(=O)O-C
    "Ether oxygen (–O–)": "[CX4][OX2H0][CX4]",         # aliphatic ether
    "Ring ether oxygen (–O– ring)": "[OX2H0;R]",
    "Primary amine (–NH₂)": "[NX3H2]",                 # -NH2
    "Secondary amine (–NH–)": "[NX3H1;!R]",            # acyclic sec amine
    "Tertiary amine (>N–)": "[NX3H0;!R]",              # acyclic tert amine
    "Ring secondary amine (–NH– ring)": "[NX3H1;R]",
    "Ring imine (>N= ring)": "[NX2H0;R]",
    "Imine (>N=)": "[NX2H0;!R]",
    "Iminium (=NH)": "[NX2H1]=*",                      # =NH
    "Nitrile (–C≡N)": "[CX2]#N",                       # -C#N carbon
    "Nitro (–NO₂)": "[$([NX3](=O)=O)]",
    "Nitroso oxygen (=O in –N=O)": "[NX2]=O",
    "Thiol (–SH)": "[SX2H1]",
    "Thioether sulfur (–S–)": "[SX2H0;!R]",
    "Ring thioether sulfur (–S– ring)": "[SX2H0;R]",
    "Fluorine (–F)": "[F]",
    "Chlorine (–Cl)": "[Cl]",
    "Bromine (–Br)": "[Br]",
    "Iodine (–I)": "[I]",
    "Vinyl carbon (=CH₂)": "[CX2H2]=[#6]",
    "Vinyl carbon (=CH–)": "[CX2H1]=[#6]",
    "Olefinic quaternary carbon (=C<)": "[CX2H0]=[#6]",
    "Cumulated diene carbon (=C=)": "[CX2]=[CX2]=[CX2]",
    "Methyl carbon (–CH₃)": "[CX4H3]",
    "Methylene carbon (–CH₂–)": "[CX4H2;!R]",
    "Ring –CH₂–": "[CX4H2;R]",
    "Methine carbon (–CH–)": "[CX4H1;!R]",
    "Ring >CH–": "[CX4H1;R]",
    "Quaternary carbon (–C–)": "[CX4H0;!R]",
    "Ring >C<": "[CX4H0;R]",
    "Ring =C<": "[cX2H0]",          # aromatic quaternary
    "Ring =CH–": "[cX2H1]",         # aromatic CH
}

_PATTERNS = {k: Chem.MolFromSmarts(v) for k, v in SMARTS.items()}


def featurize(smiles: str) -> np.ndarray | None:
    m = Chem.MolFromSmiles(smiles)
    if m is None:
        return None
    counts = np.zeros(len(COLUMNS), dtype=float)
    for i, col in enumerate(COLUMNS):
        patt = _PATTERNS.get(col)
        if patt is None:
            continue
        try:
            counts[i] = len(m.GetSubstructMatches(patt, uniquify=True))
        except Exception:
            counts[i] = 0.0
    return counts


def decode(text: str) -> np.ndarray | None:
    if not text:
        return None
    s = text.strip()
    try:
        if s.startswith("[") or s.startswith("("):
            return np.asarray(ast.literal_eval(s), dtype=float)
        return np.asarray([float(x) for x in s.replace(";", ",").split(",")], dtype=float)
    except Exception:
        return None


def vectorize(feature, vectorizer=None) -> np.ndarray:
    return np.asarray(feature, dtype=float)
