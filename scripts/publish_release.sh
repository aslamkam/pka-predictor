#!/usr/bin/env bash
# Build the pka_app_assets.tar.gz bundle and upload it as a GitHub Release asset.
# Run this AFTER the code-only commit is pushed (the release points at the repo).
#
#   scripts/publish_release.sh                  # uses default tag v1.0-models
#   PKA_RELEASE_TAG=v2.0-models scripts/publish_release.sh
#
# Requires the GitHub CLI (gh) to be installed and authenticated (gh auth login).
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
APP_DIR="$(cd "$HERE/.." && pwd)"
REPO="aslamkam/pka-predictor"
TAG="${PKA_RELEASE_TAG:-v1.0-models}"
ASSET="$APP_DIR/pka_app_assets.tar.gz"

cd "$APP_DIR"
echo ">> Building $ASSET from models/ + repo/ ..."
# Exclude runtime regenerables so the bundle stays lean.
tar --exclude='cache' --exclude='__pycache__' --exclude='*.pyc' \
    -czf "$ASSET" models repo

SIZE=$(du -h "$ASSET" | cut -f1)
echo ">> Built $ASSET ($SIZE)."

if ! command -v gh >/dev/null 2>&1; then
  echo "ERROR: gh CLI not found. Install it (https://cli.github.com) and run 'gh auth login'." >&2
  exit 1
fi

echo ">> Uploading to $REPO release $TAG ..."
if gh release view "$TAG" --repo "$REPO" >/dev/null 2>&1; then
  # Release exists — just upload (replace if already present).
  gh release upload "$TAG" "$ASSET" --repo "$REPO" --clobber
else
  gh release create "$TAG" "$ASSET" \
      --repo "$REPO" \
      --title "pKa app model assets" \
      --notes "Standard-model artifacts (~239 MB joblib) + UMA Stage-3 checkpoints (~374 MB pt) + ChEMBL feature CSVs (~115 MB). Fetched automatically on first run by scripts/fetch_assets.{sh,bat}."
fi
rm -f "$ASSET"
echo ">> Done. The fetch scripts will now resolve the asset at:"
echo "   https://github.com/$REPO/releases/download/$TAG/pka_app_assets.tar.gz"
