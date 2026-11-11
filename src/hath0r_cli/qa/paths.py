"""Path containment for QA state files written under .hath0r/."""

from __future__ import annotations

import os
from pathlib import Path


def inside(base: Path, path: Path) -> Path:
    """Resolve ``path`` and refuse anything outside ``base`` (no traversal through stored content)."""
    root = os.path.realpath(base)
    real = os.path.realpath(path)
    if not real.startswith(root + os.sep):
        raise ValueError(f"refusing to write outside {root}: {real}")
    return Path(real)
