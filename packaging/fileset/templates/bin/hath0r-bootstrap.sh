#!/usr/bin/env bash
# Minimal post-unpack checks for the HATHOR OpenSource fileset.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "==> HATHOR fileset bootstrap"
echo "    root: $ROOT"

if ! command -v hath0r >/dev/null 2>&1; then
  echo "hath0r not found on PATH."
  echo "Install: pipx install hath0r-cli   OR use a GitHub Release binary."
  exit 1
fi

echo "==> hath0r --version"
hath0r --version || true

if [[ -n "${HATH0R_GROUP_ROOT:-}" ]]; then
  echo "==> HATH0R_GROUP_ROOT=${HATH0R_GROUP_ROOT}"
fi

echo "==> hath0r doctor"
set +e
hath0r doctor
code=$?
set -e
if [[ "$code" -ne 0 ]]; then
  echo "doctor exited $code — fix named checks, then re-run."
  exit "$code"
fi

echo "bootstrap ok"
