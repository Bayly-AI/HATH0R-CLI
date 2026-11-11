"""Helpers for CCCD calibration tests: a real (deterministic) measurement command, never simulated data."""

from __future__ import annotations

import shlex
import sys
from pathlib import Path

MEASURE_SCRIPT = Path(__file__).resolve().parent / "fixtures" / "cccd_measure.py"
MEASURE_CMD = f"{shlex.quote(sys.executable)} {shlex.quote(str(MEASURE_SCRIPT))}"


def write_spec(root: Path, measure_cmd: str | None = MEASURE_CMD, replicates: int = 1) -> Path:
    """Write cfg/cccd/doe-spec.yaml under ``root`` with a measurement command."""
    import yaml

    path = root / "cfg" / "cccd" / "doe-spec.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump({"goal": "maximize", "replicates": replicates, "measure_cmd": measure_cmd}), encoding="utf-8")
    return path
