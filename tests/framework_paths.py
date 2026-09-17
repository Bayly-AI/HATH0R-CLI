"""Resolve Framework schema/contract paths for local + CI layouts."""

from __future__ import annotations

import os
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]


def framework_root() -> Path:
    """Return Framework repo root containing lib/schemas and lib/contracts.

    Order:
    1. HATH0R_FRAMEWORK_ROOT env
    2. Sibling ../hath0r (local OpenSource layout)
    3. CI checkout path ./hath0r-framework
    """
    env = os.environ.get("HATH0R_FRAMEWORK_ROOT")
    if env:
        return Path(env).expanduser().resolve()

    sibling = (_REPO_ROOT.parent / "hath0r").resolve()
    if (sibling / "lib" / "schemas").is_dir():
        return sibling

    ci = (_REPO_ROOT / "hath0r-framework").resolve()
    if (ci / "lib" / "schemas").is_dir():
        return ci

    # Last-resort historical default (local developer machine).
    legacy = Path("/Users/raybayly/Development/OpenSource/hath0r")
    if (legacy / "lib" / "schemas").is_dir():
        return legacy

    raise FileNotFoundError(
        "Framework schemas not found. Set HATH0R_FRAMEWORK_ROOT or place "
        "the Framework checkout at ../hath0r or ./hath0r-framework."
    )


def framework_schemas() -> Path:
    return framework_root() / "lib" / "schemas"


def framework_exit_codes() -> Path:
    return framework_root() / "lib" / "contracts" / "exit-codes.yaml"
