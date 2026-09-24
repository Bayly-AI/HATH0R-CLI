#!/usr/bin/env bash
# Materialize canonical group AGENTS.md / WARP.md from control tower → group root.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$ROOT/cfg/group"

if [[ -n "${GROUP_ROOT:-}" ]]; then
  DEST="$GROUP_ROOT"
elif [[ -n "${HATH0R_GROUP_ROOT:-}" ]]; then
  DEST="$HATH0R_GROUP_ROOT"
else
  # Default: parent of this tower checkout when layout is OpenSource/HATH0R-CLI
  DEST="$(cd "$ROOT/.." && pwd)"
fi

if [[ ! -f "$SRC/AGENTS.md" || ! -f "$SRC/WARP.md" ]]; then
  echo "missing canonical files under $SRC" >&2
  exit 1
fi

mkdir -p "$DEST"
stamp="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

python3 - "$SRC" "$DEST" "$stamp" <<'PY'
from pathlib import Path
import sys

src, dest, stamp = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
header = (
    f"# Synced from HATH0R-CLI/cfg/group (control tower) at {stamp}\n"
    "# Canonical git path: Bayly-AI/HATH0R-CLI → cfg/group/\n"
    "# Re-run: ./scripts/sync-group-hub.sh\n\n"
)

def body(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    stripped = text.lstrip()
    if stripped.startswith("<!--"):
        end = text.find("-->")
        if end != -1:
            text = text[end + 3 :].lstrip("\n")
    return text if text.endswith("\n") else text + "\n"

for name in ("AGENTS.md", "WARP.md"):
    out = dest / name
    out.write_text(header + body(src / name), encoding="utf-8")
    print(f"wrote {out}")
PY

echo "synced group hub policy → $DEST"
