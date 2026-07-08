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
docker run --rm -p 7860:7860 -v "$PWD/cache":/cache "$IMAGE" gui
