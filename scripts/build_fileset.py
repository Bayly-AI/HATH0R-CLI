#!/usr/bin/env python3
"""Build the HATHOR OpenSource fileset tarball (+ checksum)."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import stat
import tarfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "packaging" / "fileset" / "templates"
DEFAULT_OUT = ROOT / "dist" / "fileset"


def read_version() -> str:
    ver_path = ROOT / "VERSION"
    if ver_path.is_file():
        return ver_path.read_text(encoding="utf-8").strip()
    # fallback pyproject
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    for line in text.splitlines():
        if line.strip().startswith("version"):
            return line.split("=", 1)[1].strip().strip('"')
    return "0.0.0"


def substitute(text: str, mapping: dict[str, str]) -> str:
    out = text
    for key, value in mapping.items():
        out = out.replace(f"{{{{{key}}}}}", value)
    return out


def copy_contracts(dest: Path, framework_root: Path | None) -> list[str]:
    dest.mkdir(parents=True, exist_ok=True)
    copied: list[str] = []
    candidates: list[Path] = []
    if framework_root:
        candidates.append(framework_root / "lib" / "schemas")
        candidates.append(framework_root / "lib" / "contracts")
    # Sibling checkout default
    sibling = ROOT.parent / "hath0r"
    candidates.append(sibling / "lib" / "schemas")
    candidates.append(sibling / "lib" / "contracts")

    seen: set[str] = set()
    for base in candidates:
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*")):
            if not path.is_file():
                continue
            if path.suffix not in {".json", ".yaml", ".yml", ".md"}:
                continue
            rel = path.name
            if rel in seen:
                continue
            target = dest / rel
            shutil.copy2(path, target)
            seen.add(rel)
            copied.append(rel)
    if not copied:
        (dest / "README.md").write_text(
            "# Contracts\n\nNo Framework schemas were found at build time.\n"
            "Set `--framework-root` or place `hath0r` as a sibling checkout.\n",
            encoding="utf-8",
        )
        copied.append("README.md")
    return copied


def build(out_dir: Path, product_id: str, framework_root: Path | None) -> Path:
    cli_version = read_version()
    fileset_version = cli_version
    contracts_version = cli_version
    mapping = {
        "PRODUCT_ID": product_id,
        "FILESET_VERSION": fileset_version,
        "CLI_VERSION": cli_version,
        "CONTRACTS_VERSION": contracts_version,
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    stage_name = f"hath0r-fileset-{fileset_version}"
    stage = out_dir / stage_name
    if stage.exists():
        shutil.rmtree(stage)
    stage.mkdir(parents=True)

    # Walk templates
    for src in TEMPLATES.rglob("*"):
        if src.is_dir():
            continue
        rel = src.relative_to(TEMPLATES)
        dest = stage / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        raw = src.read_text(encoding="utf-8")
        dest.write_text(substitute(raw, mapping), encoding="utf-8")
        if src.name.endswith(".sh"):
            dest.chmod(dest.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    # LICENSE from repo root
    shutil.copy2(ROOT / "LICENSE", stage / "LICENSE")

    # contracts snapshot
    contracts_copied = copy_contracts(stage / "contracts", framework_root)

    # VERSION + MANIFEST
    (stage / "VERSION").write_text(f"{fileset_version}\n", encoding="utf-8")
    manifest = {
        "schema": "hath0r.fileset.manifest/1",
        "fileset_version": fileset_version,
        "cli_version": cli_version,
        "contracts_version": contracts_version,
        "product_id_default": product_id,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "modes": ["member", "standalone"],
        "contracts": contracts_copied,
        "engine_package": "hath0r-cli",
        "binary": "hath0r",
    }
    (stage / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    tar_path = out_dir / f"{stage_name}.tar.gz"
    if tar_path.exists():
        tar_path.unlink()
    with tarfile.open(tar_path, "w:gz") as tar:
        tar.add(stage, arcname=stage_name)

    digest = hashlib.sha256(tar_path.read_bytes()).hexdigest()
    (out_dir / f"{tar_path.name}.sha256").write_text(f"{digest}  {tar_path.name}\n", encoding="utf-8")

    print(f"fileset: {tar_path}")
    print(f"sha256:  {digest}")
    return tar_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--product-id", default="hath0r-member")
    parser.add_argument(
        "--framework-root",
        type=Path,
        default=os.environ.get("HATH0R_FRAMEWORK_ROOT"),
        help="Path to Framework checkout for schema/contracts snapshot",
    )
    args = parser.parse_args()
    fw = args.framework_root
    build(args.out, args.product_id, Path(fw) if fw else None)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
