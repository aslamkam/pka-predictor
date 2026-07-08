#!/usr/bin/env bash
# Download + extract the pKa app's model binaries (models/ + repo/) on first run.
#
# The trained standard-model artifacts (~239 MB joblib), UMA Stage-3 checkpoints
# (~374 MB pt), and ChEMBL feature CSVs (~115 MB) are too large for git/LFS, so
# they ship as a GitHub Release asset (pka_app_assets.tar.gz, ~728 MB unpacked).
# This script is idempotent: if the sentinel model already exists it exits 0.
#
# Override the download source with the PKA_ASSETS_URL env var (the directory
# that contains pka_app_assets.tar.gz) — useful for mirrors or a draft release.
#
# Requirements: curl + tar. Present on Linux/macOS and on Windows via Git Bash.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"          # .../pka_app/scripts
APP_DIR="$(cd "$HERE/.." && pwd)"              # .../pka_app
SENTINEL="$APP_DIR/models/standard/12C/Morgan-Fingerprints_RF/model.joblib"

DEFAULT_URL="https://github.com/aslamkam/jules_experiment/releases/download/v1.0-models"
URL="${PKA_ASSETS_URL:-$DEFAULT_URL}/pka_app_assets.tar.gz"

# Already fetched? Nothing to do.
if [ -f "$SENTINEL" ]; then
  exit 0
fi

echo ">> First run: fetching model assets (~728 MB download, one-time)..." >&2
echo ">>   from $URL" >&2

command -v curl >/dev/null 2>&1 || { echo "ERROR: curl not found (install it or use Git Bash)." >&2; exit 1; }
command -v tar  >/dev/null 2>&1 || { echo "ERROR: tar not found (install it or use Git Bash)." >&2; exit 1; }

TMP="$(mktemp -t pka_assets.XXXXXX.tar.gz)"
trap 'rm -f "$TMP"' EXIT

# -fL: fail on HTTP errors, follow redirects (release assets redirect to S3).
curl -fL --progress-bar -o "$TMP" "$URL"

# Sanity check: tarball should be hundreds of MB; an HTML error page would be tiny.
SIZE=$(wc -c < "$TMP" | tr -d ' ')
if [ "$SIZE" -lt 1048576 ]; then
  echo "ERROR: downloaded file is only ${SIZE} bytes — expected ~728 MB." >&2
  echo "       The asset may not be published yet, or the URL is wrong:" >&2
  echo "       $URL" >&2
  exit 1
fi

echo ">> Extracting models/ + repo/ into $APP_DIR ..." >&2
# The tarball contains top-level models/ and repo/ trees; extract in place.
tar -xzf "$TMP" -C "$APP_DIR"

if [ ! -f "$SENTINEL" ]; then
  echo "ERROR: extraction finished but sentinel $SENTINEL is still missing." >&2
  exit 1
fi
echo ">> Assets ready." >&2
