#!/usr/bin/env python3
"""Build a standalone hath0r binary via PyInstaller (optional packaging extra)."""

from __future__ import annotations

import argparse
import hashlib
import platform
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENTRY = ROOT / "packaging" / "binary" / "hath0r-entry.py"
DEFAULT_OUT = ROOT / "dist" / "binary"


def platform_tag() -> str:
    system = platform.system().lower()
    machine = platform.machine().lower()
    if system == "darwin":
        os_name = "darwin"
    elif system == "linux":
        os_name = "linux"
    elif system.startswith("win"):
        os_name = "windows"
    else:
        os_name = system
    if machine in {"x86_64", "amd64"}:
        arch = "x64"
    elif machine in {"arm64", "aarch64"}:
        arch = "arm64"
    else:
        arch = machine
    return f"{os_name}-{arch}"


def read_version() -> str:
    return (ROOT / "VERSION").read_text(encoding="utf-8").strip()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--name", default="hath0r")
    args = parser.parse_args()

    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        print(
            "PyInstaller is required. Install with:\n"
            '  pip install -e ".[release]"\n'
            "or: pip install pyinstaller",
            file=sys.stderr,
        )
        return 2

    out_dir: Path = args.out
    out_dir.mkdir(parents=True, exist_ok=True)
    work = out_dir / "work"
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)

    version = read_version()
    tag = platform_tag()
    artifact_name = f"{args.name}-{version}-{tag}"
    # PyInstaller onedir/onefile: use onefile for drop-in engine
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--name",
        args.name,
        "--distpath",
        str(work / "dist"),
        "--workpath",
        str(work / "build"),
        "--specpath",
        str(work),
        str(ENTRY),
    ]
    print("running:", " ".join(cmd))
    subprocess.check_call(cmd, cwd=ROOT)

    built = work / "dist" / (args.name + (".exe" if tag.startswith("windows") else ""))
    if not built.is_file():
        # fallback name
        candidates = list((work / "dist").glob("hath0r*"))
        if not candidates:
            print("binary not found after PyInstaller", file=sys.stderr)
            return 1
        built = candidates[0]

    final = out_dir / artifact_name
    if tag.startswith("windows"):
        final = final.with_suffix(".exe")
    shutil.copy2(built, final)
    digest = hashlib.sha256(final.read_bytes()).hexdigest()
    (out_dir / f"{final.name}.sha256").write_text(f"{digest}  {final.name}\n", encoding="utf-8")
    print(f"binary: {final}")
    print(f"sha256: {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
