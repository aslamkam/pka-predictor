"""Featurizers for the three supported standard-model feature sets.

Each featurizer exposes:
  - ``featurize(smiles) -> np.ndarray | None``           (live compute from SMILES;
    None when live compute is unavailable — Maginn)
  - ``decode(text) -> feature``                         (parse a pasted/textual feature)
  - ``vectorize(feature, vectorizer) -> np.ndarray``    (-> fixed-length numeric vector)

Morgan and Joback support live compute from an arbitrary SMILES; Maginn does not
(it needs a GCN model) and is served by ChEMBL lookup or a pasted vector.
Benson-Groups is dropped (its RMG generator only runs in a Linux Docker
container) and Orca-Sigma is excluded entirely.
"""
from . import morgan, joback, maginn, chembl_lookup, registry  # noqa: F401
