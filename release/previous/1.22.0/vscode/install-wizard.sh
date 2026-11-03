#!/usr/bin/env sh
# ==============================================================================
# Hath0r Official Install Wizard Entrypoint (HATH0R-CLI + HATH0R-MCP Docker)
# ==============================================================================
# Installs all required dependencies (Python >= 3.10, pipx, Git, curl, Docker),
# installs the hath0r CLI globally, stages the Hath0r MCP Dockerfile and
# docker-compose.yml, launches the Hath0r-MCP container on hath0r-net, and
# verifies end-to-end health.
#
# Usage:
#   ./release/install-wizard.sh [options]
#   ./release/install-wizard.sh --non-interactive --method pipx
#   ./release/install-wizard.sh --dry-run
# ==============================================================================

set -eu

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
REPO_ROOT="$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)"

if ! command -v python3 >/dev/null 2>&1; then
    echo "ERROR: python3 is required to run the Hath0r Install Wizard." >&2
    echo "Please install Python 3.10+ (https://www.python.org/downloads/ or brew/apt/dnf) and re-run." >&2
    exit 2
fi

PY_OK="$(python3 -c 'import sys; print(int(sys.version_info >= (3, 10)))' 2>/dev/null || echo 0)"
if [ "$PY_OK" != "1" ]; then
    echo "ERROR: Python 3.10 or newer is required (detected $(python3 --version 2>&1))." >&2
    exit 2
fi

if [ -f "$REPO_ROOT/scripts/install_hath0r.py" ]; then
    exec python3 "$REPO_ROOT/scripts/install_hath0r.py" "$@"
elif [ -f "$SCRIPT_DIR/install_hath0r.py" ]; then
    exec python3 "$SCRIPT_DIR/install_hath0r.py" "$@"
elif command -v hath0r >/dev/null 2>&1; then
    exec hath0r install-wizard run "$@"
else
    echo "ERROR: Could not locate install_hath0r.py or hath0r binary." >&2
    exit 1
fi
