#!/usr/bin/env bash
# Launch the pKa Predictor GUI in your browser (Linux/macOS).
# Builds the Docker image on first run, then serves the Gradio GUI on :7860.
# Predictions + extracted UMA embeddings + the uma-s-1p2 download persist in ./cache.
set -e
cd "$(dirname "$0")"
IMAGE=pkapredict
mkdir -p cache
# Fetch model binaries (~728 MB) on first run; no-op once present.
"$(dirname "$0")/scripts/fetch_assets.sh"
if ! docker image inspect "$IMAGE" >/dev/null 2>&1; then
  echo ">> Building image '$IMAGE' (first run; installs torch+fairchem — several minutes)..."
  docker build -t "$IMAGE" .
fi
echo ">> GUI starting at http://localhost:7860  (Ctrl-C to stop)"
# Resolve HuggingFace token (for the gated uma-s-1p2 model) into a --env-file.
HF_ENV="$("$(dirname "$0")/scripts/hf_env_file.sh" || true)"
cleanup_env() { [ -n "$HF_ENV" ] && [ -f "$HF_ENV" ] && rm -f "$HF_ENV"; }
trap cleanup_env EXIT
if [ -n "$HF_ENV" ]; then
  # Native Windows docker (Git Bash) needs a Windows-style path for --env-file.
  HF_ENV_NATIVE="$HF_ENV"
  command -v cygpath >/dev/null 2>&1 && HF_ENV_NATIVE="$(cygpath -w "$HF_ENV")"
  MSYS_NO_PATHCONV=1 docker run --rm -p 7860:7860 --env-file "$HF_ENV_NATIVE" -v "$PWD/cache":/cache "$IMAGE" gui
else
  echo ">> No HF_TOKEN found: UMA models will fail to download uma-s-1p2. See README." >&2
  docker run --rm -p 7860:7860 -v "$PWD/cache":/cache "$IMAGE" gui
fi
