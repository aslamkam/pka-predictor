"""Put the thesis modules on sys.path so we can import them directly:

  - Basicity_pKa_2/{model,engine,data_relaxed,infer}.py
  - DFT/FairChem/uma_relaxed_pipeline.py
  - repo-root pytorch_sklearn_wrapper.py
"""
from __future__ import annotations

import sys

from .. import config

for p in (config.BASICITY_DIR, config.REPO_ROOT,
          config.REPO_ROOT / "DFT" / "FairChem"):
    sp = str(p)
    if p.exists() and sp not in sys.path:
        sys.path.insert(0, sp)
