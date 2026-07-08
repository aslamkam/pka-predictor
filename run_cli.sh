#!/usr/bin/env bash
# Run the pKa Predictor CLI inside Docker (Linux/macOS).
#   ./run_cli.sh list
#   ./run_cli.sh predict --smiles "C1CCCN1" --models uma-invt,std-12C-Morgan-Fingerprints-RF --temp 298.15
#   ./run_cli.sh plot --smiles "C1CCCN1" --model uma-invt --n 10 --step 10 --unit C
set -e
cd "$(dirname "$0")"
IMAGE=pkapredict
mkdir -p cache
# Fetch model binaries (~728 MB) on first run; no-op once present.
"$(dirname "$0")/scripts/fetch_assets.sh"
if ! docker image inspect "$IMAGE" >/dev/null 2>&1; then
  echo ">> Building image '$IMAGE' (first run)..." >&2
  docker build -t "$IMAGE" . >&2
fi
# Resolve HuggingFace token (for the gated uma-s-1p2 model) into a --env-file.
HF_ENV="$("$(dirname "$0")/scripts/hf_env_file.sh" || true)"
cleanup_env() { [ -n "$HF_ENV" ] && [ -f "$HF_ENV" ] && rm -f "$HF_ENV"; }
trap cleanup_env EXIT
if [ -n "$HF_ENV" ]; then
  HF_ENV_NATIVE="$HF_ENV"
  command -v cygpath >/dev/null 2>&1 && HF_ENV_NATIVE="$(cygpath -w "$HF_ENV")"
  MSYS_NO_PATHCONV=1 docker run --rm -i --env-file "$HF_ENV_NATIVE" -v "$PWD/cache":/cache "$IMAGE" "$@"
else
  docker run --rm -i -v "$PWD/cache":/cache "$IMAGE" "$@"
fi
