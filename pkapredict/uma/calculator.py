"""Singleton FairChem ``uma-s-1p2`` calculator + embedding hooks.

Reuses ``DFT/FairChem/uma_relaxed_pipeline.worker_init`` (constructs the
FAIRChemCalculator, registers the penultimate + backbone hooks that
``get_relaxed_embeddings`` reads). Loading is heavy (~10–60 s, + the uma-s-1p2
checkpoint downloads from HuggingFace on first use, then cached), so it is done
once per process.
"""
from __future__ import annotations

from . import _paths  # noqa: F401  (sys.path setup)


def _import_pipeline():
    import uma_relaxed_pipeline as pipe   # from DFT/FairChem on sys.path
    return pipe


_CACHE: dict = {}


def get_calculator():
    """Return (pipeline_module, calculator, head). Constructs on first call."""
    if "pipe" in _CACHE:
        return _CACHE["pipe"], _CACHE["calc"], _CACHE["head"]
    pipe = _import_pipeline()
    # worker_init sets pipe.worker_calc / pipe.worker_head and registers the hooks
    # on MLP_EFS_Head.energy_block[3] (penultimate) and the eSCN backbone norm.
    pipe.worker_init()
    if pipe.worker_calc is None or pipe.worker_head is None:
        raise RuntimeError("uma-s-1p2 calculator failed to initialise "
                           "(see messages above; first use downloads the checkpoint).")
    _CACHE["pipe"] = pipe
    _CACHE["calc"] = pipe.worker_calc
    _CACHE["head"] = pipe.worker_head
    return pipe, pipe.worker_calc, pipe.worker_head
