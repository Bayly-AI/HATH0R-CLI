"""HATH0R CLI — operator/developer control plane."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

_FALLBACK_VERSION = "0.2.0"


def _package_version() -> str:
    try:
        ver_file = Path(__file__).resolve().parents[2] / "VERSION"
        if ver_file.is_file():
            ver = ver_file.read_text(encoding="utf-8").strip()
            if ver:
                return ver
    except Exception:
        pass
    try:
        return version("hath0r-cli")
    except PackageNotFoundError:
        return _FALLBACK_VERSION


__version__ = _package_version()
