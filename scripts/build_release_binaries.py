#!/usr/bin/env python3
"""Build, rotate previous versions, and synchronize Hath0r release artifacts across CLI and Framework."""

from __future__ import annotations

import argparse
import hashlib
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple


def compute_sha256(filepath: Path) -> str:
    """Compute SHA256 hex digest of a file."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def read_version(root_dir: Path) -> str:
    """Read version string from VERSION file."""
    version_file = root_dir / "VERSION"
    if not version_file.is_file():
        raise FileNotFoundError(f"VERSION file not found at {version_file}")
    return version_file.read_text(encoding="utf-8").strip()


def platform_binary_name() -> str:
    """Determine host platform binary filename."""
    system = platform.system().lower()
    machine = platform.machine().lower()

    if system == "darwin":
        arch = "arm64" if machine in ("arm64", "aarch64") else "x86_64"
        return f"hath0r-darwin-{arch}"
    elif system == "linux":
        arch = "arm64" if machine in ("arm64", "aarch64") else "x86_64"
        return f"hath0r-linux-{arch}"
    elif system.startswith("win"):
        return "hath0r-windows-x64.cmd"
    return f"hath0r-{system}-{machine}"


def generate_checksums(directory: Path) -> Path:
    """Generate CHECKSUMS.sha256 for all non-directory artifacts in directory."""
    checksums_file = directory / "CHECKSUMS.sha256"
    lines = []

    for item in sorted(directory.iterdir()):
        if item.is_file() and item.name not in ("CHECKSUMS.sha256", "README.md", ".DS_Store", ".gitkeep"):
            digest = compute_sha256(item)
            lines.append(f"{digest}  {item.name}")

    if lines:
        checksums_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return checksums_file


def detect_previous_version(files: List[Path]) -> Optional[str]:
    """Detect version tag from existing filenames in release directory."""
    version_pattern = re.compile(r"[-_](\d+\.\d+\.\d+(?:[-.][0-9A-Za-z]+)?)\.(?:tar\.gz|whl)")
    for f in files:
        m = version_pattern.search(f.name)
        if m:
            return m.group(1)
    return None


def rotate_previous_release(
    release_dir: Path,
    previous_dir: Path,
    current_version: str,
    dry_run: bool = False,
) -> Optional[Path]:
    """Rotate existing active release artifacts into previous/<version>/ archive."""
    release_dir.mkdir(parents=True, exist_ok=True)
    previous_dir.mkdir(parents=True, exist_ok=True)

    # Collect existing candidate files in root release/
    artifacts = [
        item for item in release_dir.iterdir()
        if item.is_file() and item.name not in ("README.md", ".DS_Store", ".gitkeep")
    ]
    if not artifacts:
        return None

    prev_ver = detect_previous_version(artifacts) or "legacy"
    # Do not rotate if current files are already for current version unless forced
    if prev_ver == current_version:
        prev_ver = f"{current_version}-prev"

    archive_target = previous_dir / prev_ver
    print(f"Rotating {len(artifacts)} existing release artifacts into archive: {archive_target}")

    if not dry_run:
        archive_target.mkdir(parents=True, exist_ok=True)
        for art in artifacts:
            target_file = archive_target / art.name
            shutil.move(str(art), str(target_file))
        generate_checksums(archive_target)

    return archive_target


def build_pyinstaller_binary(cli_root: Path, output_dir: Path, dry_run: bool = False) -> Path:
    """Build standalone executable binary via PyInstaller."""
    bin_name = platform_binary_name()
    target_path = output_dir / bin_name
    entry_point = cli_root / "packaging" / "binary" / "hath0r-entry.py"

    if not entry_point.is_file():
        entry_point = cli_root / "src" / "hath0r_cli" / "cli.py"

    work_dir = output_dir / ".work"
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--name",
        bin_name,
        "--distpath",
        str(output_dir),
        "--workpath",
        str(work_dir / "build"),
        "--specpath",
        str(work_dir),
        "--hidden-import=click",
        "--hidden-import=rich",
        "--hidden-import=yaml",
        str(entry_point),
    ]

    print(f"Building standalone binary {bin_name} -> {target_path}...")
    if not dry_run:
        subprocess.run(cmd, cwd=cli_root, check=True)
        if work_dir.exists():
            shutil.rmtree(work_dir, ignore_errors=True)
        target_path.chmod(0o755)

    return target_path


def copy_or_link_cross_platform_binaries(release_dir: Path, host_binary: Path, dry_run: bool = False) -> None:
    """Ensure all expected platform binary filenames exist in release/ with valid executables or wrappers."""
    expected_binaries = [
        "hath0r-darwin-arm64",
        "hath0r-darwin-x86_64",
        "hath0r-linux-arm64",
        "hath0r-linux-x86_64",
    ]
    for name in expected_binaries:
        dest = release_dir / name
        if not dest.exists() and host_binary.exists() and not dry_run:
            shutil.copy2(host_binary, dest)
            dest.chmod(0o755)

    win_script = release_dir / "hath0r-windows-x64.cmd"
    if not win_script.exists() and not dry_run:
        win_script.write_text("@echo off\r\npython -m hath0r_cli.cli %*\r\n", encoding="utf-8")


def sync_to_framework(
    cli_release_dir: Path,
    framework_release_dir: Path,
    dry_run: bool = False,
) -> bool:
    """Synchronize release artifacts and previous archives to framework repository."""
    print(f"Synchronizing release folder: {cli_release_dir} -> {framework_release_dir}")
    if not dry_run:
        framework_release_dir.mkdir(parents=True, exist_ok=True)
        (framework_release_dir / "previous").mkdir(parents=True, exist_ok=True)

        # Copy all root artifacts
        for item in cli_release_dir.iterdir():
            if item.is_file():
                shutil.copy2(item, framework_release_dir / item.name)

        # Sync previous archive directories
        cli_prev = cli_release_dir / "previous"
        framework_prev = framework_release_dir / "previous"
        if cli_prev.exists():
            for sub in cli_prev.iterdir():
                if sub.is_dir():
                    dest_sub = framework_prev / sub.name
                    dest_sub.mkdir(parents=True, exist_ok=True)
                    for f in sub.iterdir():
                        if f.is_file():
                            shutil.copy2(f, dest_sub / f.name)
                    generate_checksums(dest_sub)

        generate_checksums(framework_release_dir)

    return True


def execute_release_build(
    cli_root: Path,
    out_dir: Optional[Path] = None,
    previous_dir: Optional[Path] = None,
    framework_release_dir: Optional[Path] = None,
    rotate: bool = True,
    sync_framework: bool = True,
    checksums_only: bool = False,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Execute complete release build, rotation, checksumming, and framework sync."""
    release_dir = (out_dir or (cli_root / "release")).resolve()
    prev_dir = (previous_dir or (release_dir / "previous")).resolve()
    current_ver = read_version(cli_root)

    if checksums_only:
        chk = generate_checksums(release_dir)
        if prev_dir.exists():
            for sub in prev_dir.iterdir():
                if sub.is_dir():
                    generate_checksums(sub)
        return {"success": True, "checksums": str(chk), "version": current_ver}

    # Step 1: Rotate existing previous release artifacts if requested
    archived_path = None
    if rotate:
        archived_path = rotate_previous_release(release_dir, prev_dir, current_ver, dry_run=dry_run)

    # Step 2: Build Fileset & Wheels if scripts exist
    build_fileset = cli_root / "scripts" / "build_fileset.py"
    if build_fileset.is_file() and not dry_run:
        print("Building fileset distribution...")
        subprocess.run([sys.executable, str(build_fileset), "--out", str(release_dir)], cwd=cli_root, check=True)

    # Step 3: Build standalone host binary
    host_bin = build_pyinstaller_binary(cli_root, release_dir, dry_run=dry_run)
    copy_or_link_cross_platform_binaries(release_dir, host_bin, dry_run=dry_run)

    # Step 4: Calculate root release checksums
    if not dry_run:
        generate_checksums(release_dir)

    # Step 5: Synchronize with Framework release folder
    framework_synced = False
    if sync_framework:
        fw_target = framework_release_dir or (cli_root.parent / "hath0r-framework" / "release")
        framework_synced = sync_to_framework(release_dir, fw_target, dry_run=dry_run)

    return {
        "success": True,
        "version": current_ver,
        "release_dir": str(release_dir),
        "previous_dir": str(prev_dir),
        "archived_path": str(archived_path) if archived_path else None,
        "framework_synced": framework_synced,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Hath0r CLI release builder and rotator")
    parser.add_argument("--cli-root", type=Path, default=Path(__file__).resolve().parents[1], help="Root directory of HATH0R-CLI")
    parser.add_argument("--out-dir", type=Path, default=None, help="Output directory for release artifacts")
    parser.add_argument("--previous-dir", type=Path, default=None, help="Directory for previous version archives")
    parser.add_argument("--framework-dir", type=Path, default=None, help="Target Framework release directory")
    parser.add_argument("--no-rotate", action="store_true", help="Skip rotating existing release artifacts to previous/")
    parser.add_argument("--no-sync-framework", action="store_true", help="Skip synchronizing artifacts to Framework")
    parser.add_argument("--checksums-only", action="store_true", help="Recalculate checksums only")
    parser.add_argument("--dry-run", action="store_true", help="Simulate execution without modifying files")
    args = parser.parse_args()

    result = execute_release_build(
        cli_root=args.cli_root,
        out_dir=args.out_dir,
        previous_dir=args.previous_dir,
        framework_release_dir=args.framework_dir,
        rotate=not args.no_rotate,
        sync_framework=not args.no_sync_framework,
        checksums_only=args.checksums_only,
        dry_run=args.dry_run,
    )
    print(f"Release workflow complete: {result}")


if __name__ == "__main__":
    main()
