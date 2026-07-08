# pKa Predictor — Docker image (GUI + CLI).
#
# Default build is CPU (portable, runs anywhere Docker does — no GPU needed).
# For a CUDA GPU image pass --build-arg BASE=pytorch/pytorch:2.8.0-cuda12.6-cudnn9-runtime.
#
#   docker build -t pkapredict .                          # CPU (default)
#   docker build --build-arg BASE=pytorch/pytorch:2.8.0-cuda12.6-cudnn9-runtime -t pkapredict .   # GPU
#   docker run --rm -p 7860:7860 -v "$PWD/cache":/cache pkapredict gui
#
# NOTE: the official pytorch/pytorch image has NO "-cpu" tag (PyTorch only
# publishes CUDA images). The CPU default therefore builds on python:3.11 and
# installs the CPU-only torch wheels from https://download.pytorch.org/whl/cpu.
ARG BASE=python:3.11-slim
FROM ${BASE}

# When the caller overrides BASE with a CUDA image (which already ships torch),
# skip reinstalling torch; otherwise install the CPU-only wheels.
ARG INSTALL_CPU_TORCH=1
ENV DISABLE_CUDA_EXTENSION=1 \
    PYTHONUNBUFFERED=1 \
    HF_HUB_DOWNLOAD_TIMEOUT=120 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN if [ "${INSTALL_CPU_TORCH}" = "1" ]; then \
      pip install --no-cache-dir torch==2.8.0 --index-url https://download.pytorch.org/whl/cpu ; \
    fi

# fairchem-core's CUDA extension is opt-in; the pure-PyTorch fallback works on CPU
# images, so we can install it regardless of BASE.
RUN pip install --no-cache-dir \
        "fairchem-core>=1.4" "rdkit>=2023.3" "scikit-learn>=1.3" "xgboost>=2.0" \
        "gradio>=4.0" "matplotlib>=3.7" "pandas>=2.0" "ase>=3.22" "joblib>=1.3"

WORKDIR /app
COPY . /app/

# Persist predictions, extracted embeddings, and the uma-s-1p2 download under
# /cache (mount it: -v <host>/cache:/cache). HOME=/cache puts ~/.cache
# (fairchem + huggingface) there too, so uma-s-1p2 downloads once and survives.
ENV PKA_APP_ROOT=/app \
    PKA_REPO_ROOT=/app/repo \
    PKA_CACHE_DIR=/cache \
    PKA_EMB_GLOBAL_DIR=/cache/embeddings/global \
    PKA_EMB_LOCAL_DIR=/cache/embeddings/local \
    HOME=/cache
RUN mkdir -p /cache/embeddings/global /cache/embeddings/local

EXPOSE 7860
VOLUME ["/cache"]
ENTRYPOINT ["python", "/app/cli.py"]
CMD ["gui"]
