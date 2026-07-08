"""pKa Predictor — predict pKa from SMILES with standard ML models or the
FairChem UMA Basicity model. See README.md / config.py for layout."""

__version__ = "0.1.0"


def __getattr__(name):
    # Lazy import so submodules (config, smiles_util, featurizers, ...) import
    # cleanly even before core/uma are present, and heavy deps (torch, fairchem)
    # only load when actually used.
    if name in ("predict", "predict_many", "sweep_temperature"):
        from . import core
        return getattr(core, name)
    raise AttributeError(f"module 'pkapredict' has no attribute {name!r}")
