"""Safe writes for QA state files kept under .hath0r/."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

_STATE_NAME_RE = re.compile(r"[a-z0-9][a-z0-9_-]{0,63}\.json")


def write_state_json(base: Path, name: str, payload: Any) -> Path:
    """Atomically write ``payload`` as ``base/name``.

    ``name`` must be a plain lowercase ``*.json`` file name. The target is always a direct child of
    ``base``, so stored content can never steer a write elsewhere.
    """
    if not _STATE_NAME_RE.fullmatch(name):
        raise ValueError(f"invalid state file name: {name!r}")
    root = os.path.realpath(base)
    os.makedirs(root, exist_ok=True)
    safe_name = os.path.basename(name)
    target = os.path.join(root, safe_name)
    tmp = os.path.join(root, safe_name[: -len(".json")] + ".tmp")
    with open(tmp, "w", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, indent=2, default=str))
    os.replace(tmp, target)
    return Path(target)
