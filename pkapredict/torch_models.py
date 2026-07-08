"""Torch module + trainer + predictor for the standard-model MLP/CNN.

Self-contained (no SklearnWrapper) so training is robust and the saved artifact
(a ``TorchPredictor`` holding a state_dict + config) joblib-round-trips in any
process that imports ``pkapredict``.
"""
from __future__ import annotations

import copy
import os

import numpy as np
import torch
import torch.nn as nn


class TorchMLP(nn.Module):
    def __init__(self, input_size, hidden_layer_sizes=(128, 64)):
        super().__init__()
        sizes = [input_size] + list(hidden_layer_sizes) + [1]
        layers = []
        for i in range(len(sizes) - 1):
            layers.append(nn.Linear(sizes[i], sizes[i + 1]))
            if i < len(sizes) - 2:
                layers.append(nn.ReLU())
        self.net = nn.Sequential(*layers)

    def forward(self, x):
        return self.net(x)


class CNN1D(nn.Module):
    """1D conv over the feature vector with adaptive pooling (any input width)."""
    def __init__(self, input_size, channels=24, kernel=5):
        super().__init__()
        k = max(3, kernel)
        pad = k // 2
        self.conv = nn.Sequential(
            nn.Conv1d(1, channels, k, padding=pad), nn.ReLU(),
            nn.Conv1d(channels, channels * 2, k, padding=pad), nn.ReLU(),
            nn.AdaptiveAvgPool1d(1),
        )
        self.head = nn.Sequential(nn.Linear(channels * 2, 64), nn.ReLU(), nn.Linear(64, 1))

    def forward(self, x):               # x: (B, D)
        h = x.unsqueeze(1).float()
        h = self.conv(h).squeeze(-1)
        return self.head(h)


_BUILDERS = {"MLP": TorchMLP, "CNN": CNN1D}
_ARCH_DEFAULTS = {
    "MLP": {"hidden_layer_sizes": [128, 64]},
    "CNN": {"channels": 24, "kernel": 5},
}


class TorchPredictor:
    """Picklable predictor: rebuilds its module from the saved state_dict."""
    def __init__(self, kind: str, input_size: int, arch: dict, state_dict: dict):
        self.kind = kind
        self.input_size = int(input_size)
        self.arch = dict(arch)
        self.state_dict = state_dict
        self._model = None

    def _build(self):
        m = _BUILDERS[self.kind](input_size=self.input_size, **self.arch)
        if self.state_dict:
            m.load_state_dict(self.state_dict)
        m.eval()
        return m

    def predict(self, X) -> np.ndarray:
        if self._model is None:
            self._model = self._build()
        with torch.no_grad():
            xt = torch.as_tensor(np.asarray(X, dtype="float32"))
            out = self._model(xt).cpu().numpy().reshape(-1)
        return out


def train_torch(kind: str, X_tr, y_tr, X_val=None, y_val=None,
                epochs: int = 40, lr: float = 1e-3, batch_size: int = 256,
                patience: int = 8, seed: int = 42, arch: dict | None = None) -> TorchPredictor:
    """Train a TorchMLP/CNN1D with early stopping. Returns a TorchPredictor."""
    try:
        torch.set_num_threads(max(1, (os.cpu_count() or 2) // 2))
    except Exception:
        pass
    torch.manual_seed(seed)
    input_size = X_tr.shape[1]
    arch = dict(_ARCH_DEFAULTS.get(kind, {}), **(arch or {}))
    model = _BUILDERS[kind](input_size=input_size, **arch)
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    loss_fn = nn.MSELoss()

    Xtr = torch.as_tensor(X_tr, dtype=torch.float32)
    ytr = torch.as_tensor(y_tr, dtype=torch.float32).view(-1, 1)
    if X_val is None or len(X_val) == 0:
        # carve a small val set for early stopping
        rng = torch.randperm(len(Xtr))
        nv = max(1, len(Xtr) // 10)
        X_val = Xtr[rng[:nv]]; y_val = ytr[rng[:nv]]
        Xtr = Xtr[rng[nv:]]; ytr = ytr[rng[nv:]]
    Xv = torch.as_tensor(X_val, dtype=torch.float32)
    yv = torch.as_tensor(y_val, dtype=torch.float32).view(-1, 1)

    best_loss, best_state, bad = float("inf"), None, 0
    n = len(Xtr)
    for ep in range(epochs):
        model.train()
        perm = torch.randperm(n)
        for i in range(0, n, batch_size):
            idx = perm[i:i + batch_size]
            opt.zero_grad()
            loss = loss_fn(model(Xtr[idx]), ytr[idx])
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
        model.eval()
        with torch.no_grad():
            vl = float(loss_fn(model(Xv), yv))
        if vl + 1e-6 < best_loss:
            best_loss, best_state, bad = vl, copy.deepcopy(model.state_dict()), 0
        else:
            bad += 1
            if bad >= patience:
                break
    if best_state is None:
        best_state = model.state_dict()
    return TorchPredictor(kind, input_size, arch, best_state)
