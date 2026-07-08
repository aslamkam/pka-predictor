"""Featurizers for the four supported standard-model feature sets.

Each featurizer exposes:
  - ``featurize(smiles) -> np.ndarray | dict | None``  (live compute from SMILES;
    None when live compute is unavailable — Benson/Maginn)
  - ``decode(text) -> feature``                         (parse a pasted/textual feature)
  - ``vectorize(feature, vectorizer) -> np.ndarray``    (-> fixed-length numeric vector)

Morgan and Joback support live compute from an arbitrary SMILES; Benson and
Maginn do not (they need RMG / a GCN model) and are served by ChEMBL lookup or a
pasted vector. Orca-Sigma is excluded entirely.
"""
from . import morgan, joback, benson, maginn, chembl_lookup, registry  # noqa: F401
