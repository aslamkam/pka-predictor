#!/usr/bin/env bash
# Resolve the HuggingFace token and write it to a --env-file for `docker run`.
#
# Source priority:
#   1. $HF_TOKEN environment variable (if set)
#   2. .hf_token file in the pka_app/ dir (parent of this scripts/ dir)
#
# Prints the env-file path to stdout (caller passes it via --env-file to
# docker run). Prints an empty line if no token found (caller omits --env-file).
#
# Using --env-file (not --env on the CLI) keeps the token out of `ps`/process
# listings. The temp file is mode 600 and removed by the caller after the run.
#
# The temp file is placed in the cache/ dir (gitignored + always present) so its
# path is repo-relative: native Windows docker can resolve it without cygpath
# translation even when this script runs under Git Bash.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
APP_DIR="$(cd "$HERE/.." && pwd)"
TOKEN=""

if [ -n "${HF_TOKEN:-}" ]; then
  TOKEN="$HF_TOKEN"
elif [ -f "$APP_DIR/.hf_token" ]; then
  # Trim trailing whitespace/newlines.
  TOKEN="$(tr -d '[:space:]' < "$APP_DIR/.hf_token")"
fi

if [ -z "$TOKEN" ]; then
  echo ""
  exit 0
fi

mkdir -p "$APP_DIR/cache"
ENVFILE="$APP_DIR/cache/.hf_env"
chmod 600 "$ENVFILE" 2>/dev/null || true
printf 'HF_TOKEN=%s\n' "$TOKEN" > "$ENVFILE"
chmod 600 "$ENVFILE" 2>/dev/null || true
echo "$ENVFILE"
