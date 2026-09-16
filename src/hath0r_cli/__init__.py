"""HATH0R CLI — operator/developer control plane."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

_FALLBACK_VERSION = "0.2.0"


def _package_version() -> str:
    try:
        return version("hath0r-cli")
    except PackageNotFoundError:
        return _FALLBACK_VERSION


__version__ = _package_version()
