#!/usr/bin/env python3
"""Build standalone Hath0r CLI release artifacts, rotate mac/windows/vscode to previous/<version>/, and sync with Framework."""

from __future__ import annotations

import argparse
import hashlib
import platform
import re
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path
from typing import Any, Dict, List, Optional

PLATFORM_FOLDERS = ("mac", "windows", "vscode")



def pyinstaller_bundle_args() -> list:
    """Flags that make the frozen binary carry every command.

    Subcommands load through importlib (lazy_group.COMMAND_REGISTRY) and the bots import
    hath0r_engine from the framework, so PyInstaller's static scan misses both. Without these
    the binary answers "No such command" for install-wizard, release, evals and more, and
    reports a stale version because the package metadata is not bundled.
    """
    import importlib.util

    args = ["--collect-submodules", "hath0r_cli", "--copy-metadata", "hath0r-cli"]
    spec = importlib.util.find_spec("hath0r_engine")
    if spec is not None:
        # An editable install resolves through a setuptools finder that PyInstaller does not
        # follow, so point it at the directory that holds the package as well.
        locations = list(spec.submodule_search_locations or [])
        if locations:
            args += ["--paths", str(Path(locations[0]).parent)]
        args += ["--collect-submodules", "hath0r_engine"]
    return args

def read_version(cli_root: Path) -> str:
    """Read current SemVer from VERSION file."""
    ver_file = cli_root / "VERSION"
    if not ver_file.is_file():
        raise FileNotFoundError(f"VERSION file not found in {cli_root}")
    return ver_file.read_text(encoding="utf-8").strip()


def platform_binary_name() -> str:
    """Determine canonical binary name for the current host OS and architecture."""
    sys_name = platform.system().lower()
    mach = platform.machine().lower()
    if mach in ("x86_64", "amd64"):
        arch = "x86_64"
    elif mach in ("arm64", "aarch64"):
        arch = "arm64"
    else:
        arch = mach

    if sys_name == "darwin":
        return f"hath0r-darwin-{arch}"
    elif sys_name == "linux":
        return f"hath0r-linux-{arch}"
    elif sys_name == "windows":
        return "hath0r-windows-x64.exe"
    return f"hath0r-{sys_name}-{arch}"


def compute_sha256(file_path: Path) -> str:
    """Compute SHA-256 hex digest of a file."""
    h = hashlib.sha256()
    with file_path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def generate_checksums(target_dir: Path) -> Path:
    """Generate CHECKSUMS.sha256 for all release artifacts in target_dir (and platform subfolders if at release/ root)."""
    checksum_file = target_dir / "CHECKSUMS.sha256"
    lines: List[str] = []
    if not target_dir.is_dir():
        return checksum_file

    for item in sorted(target_dir.iterdir()):
        if item.is_file() and item.name not in (
            "CHECKSUMS.sha256",
            "README.md",
            "AGENTS.md",
            ".DS_Store",
            ".gitkeep",
        ):
            if item.name.endswith(".sha256"):
                continue
            digest = compute_sha256(item)
            lines.append(f"{digest}  {item.name}")

    # If target_dir has mac/, windows/, vscode/ subfolders, also index their primary artifacts
    for sub_name in PLATFORM_FOLDERS:
        sub_dir = target_dir / sub_name
        if sub_dir.is_dir():
            for item in sorted(sub_dir.iterdir()):
                if item.is_file() and item.name not in ("CHECKSUMS.sha256", "README.md", ".DS_Store", ".gitkeep"):
                    if item.name.endswith(".sha256"):
                        continue
                    digest = compute_sha256(item)
                    lines.append(f"{digest}  {sub_name}/{item.name}")

    checksum_file.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    return checksum_file


def detect_previous_version(artifacts: List[Path], exclude_version: Optional[str] = None) -> Optional[str]:
    """Extract version string from existing tarball/wheel/installer filenames in release directory."""
    ver_pattern = re.compile(r"[-_](\d+\.\d+\.\d+)(?:[-._]|$)")
    versions_found: List[str] = []
    for item in artifacts:
        m = ver_pattern.search(item.name)
        if m:
            ver = m.group(1)
            if exclude_version and ver == exclude_version:
                continue
            versions_found.append(ver)
    if versions_found:
        return sorted(set(versions_found))[-1]
    return None


def _route_artifact_to_platform_folders(
    item: Path,
    release_dir: Path,
    current_version: str,
    dry_run: bool = False,
) -> List[str]:
    """Route a current-version loose artifact into `release/mac/`, `release/windows/`, or `release/vscode/`."""
    routed: List[str] = []
    mac_dir = release_dir / "mac"
    win_dir = release_dir / "windows"
    vscode_dir = release_dir / "vscode"
    name = item.name

    is_mac_only = (
        name.endswith(".dmg")
        or name.endswith(".dmg.sha256")
        or "darwin" in name
        or "-macos" in name
    )
    is_win_only = (
        name.endswith(".exe")
        or name.endswith(".exe.sha256")
        or "windows" in name
        or name.endswith(".cmd")
    )
    is_vscode_only = name.endswith(".vsix") or name.endswith(".vsix.sha256")
    is_shared_installer = (
        name in ("install_hath0r.py", "install-wizard.sh")
        or name.startswith(f"hath0r-fileset-{current_version}")
    )

    if not dry_run:
        mac_dir.mkdir(parents=True, exist_ok=True)
        win_dir.mkdir(parents=True, exist_ok=True)
        vscode_dir.mkdir(parents=True, exist_ok=True)

    if is_mac_only:
        routed.append(f"mac/{name}")
        if not dry_run:
            shutil.move(str(item), str(mac_dir / name))
    elif is_win_only:
        routed.append(f"windows/{name}")
        if not dry_run:
            shutil.move(str(item), str(win_dir / name))
    elif is_vscode_only:
        routed.append(f"vscode/{name}")
        if not dry_run:
            shutil.move(str(item), str(vscode_dir / name))
    elif is_shared_installer:
        routed.extend([f"mac/{name}", f"windows/{name}"])
        if not dry_run:
            shutil.copy2(item, mac_dir / name)
            shutil.move(str(item), str(win_dir / name))
    else:
        # Remove other loose platform files (e.g. linux binary at root if already archived)
        if not dry_run and item.exists():
            item.unlink(missing_ok=True)
    return routed


def cleanup_and_archive_release_dir(
    release_dir: Path,
    previous_dir: Path,
    current_version: str,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Ensure `release/{mac,windows,vscode}` hold only `current_version` and all older versions are in `release/previous/<ver>/`."""
    release_dir.mkdir(parents=True, exist_ok=True)
    previous_dir.mkdir(parents=True, exist_ok=True)
    for sub_name in PLATFORM_FOLDERS:
        if not dry_run:
            (release_dir / sub_name).mkdir(parents=True, exist_ok=True)

    # Remove any temporary `Stable` folder if present
    stable_dir = release_dir / "Stable"
    if stable_dir.is_dir() and not dry_run:
        for child in stable_dir.iterdir():
            if child.is_dir() and child.name in PLATFORM_FOLDERS:
                dest_plat = release_dir / child.name
                dest_plat.mkdir(parents=True, exist_ok=True)
                for f in child.iterdir():
                    if f.name != ".DS_Store":
                        shutil.move(str(f), str(dest_plat / f.name))
        shutil.rmtree(stable_dir, ignore_errors=True)

    archived_versions: set[str] = set()
    removed_temp_dirs: List[str] = []
    moved_files: List[str] = []

    fileset_dir_re = re.compile(r"^hath0r-fileset-(\d+\.\d+\.\d+)$")
    version_file_re = re.compile(r"[-_](\d+\.\d+\.\d+)(?:[-._]|$)")
    strict_semver_re = re.compile(r"^\d+\.\d+\.\d+$")

    # 0. Clean up any loose files sitting directly inside release/previous/ (outside a <ver>/ subfolder)
    if previous_dir.is_dir():
        for item in sorted(previous_dir.iterdir()):
            if not item.is_file() or item.name in ("README.md", ".DS_Store", ".gitkeep"):
                continue
            if item.name == "CHECKSUMS.sha256":
                if not dry_run:
                    item.unlink(missing_ok=True)
                continue
            m_prev_file = version_file_re.search(item.name)
            if m_prev_file:
                f_ver = m_prev_file.group(1)
                if f_ver != current_version:
                    moved_files.append(f"previous/{item.name}->previous/{f_ver}/{item.name}")
                    archived_versions.add(f_ver)
                    if not dry_run:
                        ver_sub = previous_dir / f_ver
                        ver_sub.mkdir(parents=True, exist_ok=True)
                        shutil.move(str(item), str(ver_sub / item.name))
                else:
                    moved_files.extend(_route_artifact_to_platform_folders(item, release_dir, current_version, dry_run))
            else:
                moved_files.extend(_route_artifact_to_platform_folders(item, release_dir, current_version, dry_run))

        # Normalize any non-semver folders in previous/ and split mixed versions inside previous/<ver>/
        for sub in sorted(previous_dir.iterdir()):
            if not sub.is_dir():
                continue
            if not strict_semver_re.match(sub.name):
                m_sub = re.match(r"^(\d+\.\d+\.\d+)", sub.name)
                if not dry_run:
                    if m_sub and m_sub.group(1) != current_version:
                        proper_prev = previous_dir / m_sub.group(1)
                        proper_prev.mkdir(parents=True, exist_ok=True)
                        for f in sub.iterdir():
                            if f.is_file() and f.name != "CHECKSUMS.sha256":
                                shutil.move(str(f), str(proper_prev / f.name))
                        archived_versions.add(m_sub.group(1))
                    shutil.rmtree(sub, ignore_errors=True)
            else:
                folder_ver = sub.name
                for f in sorted(sub.iterdir()):
                    if not f.is_file() or f.name in ("CHECKSUMS.sha256", "README.md", ".DS_Store"):
                        continue
                    mf = version_file_re.search(f.name)
                    if mf and mf.group(1) != folder_ver:
                        true_ver = mf.group(1)
                        moved_files.append(f"{folder_ver}/{f.name}->{true_ver}/{f.name}")
                        archived_versions.add(folder_ver)
                        archived_versions.add(true_ver)
                        if not dry_run:
                            true_dir = previous_dir / true_ver
                            true_dir.mkdir(parents=True, exist_ok=True)
                            shutil.move(str(f), str(true_dir / f.name))

    # 1. Clean up unpacked hath0r-fileset-<ver>/ staging directories in release/
    for item in sorted(release_dir.iterdir()):
        if not item.is_dir() or item.name in ("previous", "mac", "windows", "vscode", "prompts", ".work"):
            continue
        m_dir = fileset_dir_re.match(item.name)
        if m_dir:
            ver = m_dir.group(1)
            removed_temp_dirs.append(item.name)
            if not dry_run:
                if ver != current_version:
                    ver_prev = previous_dir / ver
                    ver_prev.mkdir(parents=True, exist_ok=True)
                    tar_dest = ver_prev / f"{item.name}.tar.gz"
                    if not tar_dest.is_file():
                        with tarfile.open(tar_dest, "w:gz") as tar:
                            tar.add(item, arcname=item.name)
                        digest = compute_sha256(tar_dest)
                        (ver_prev / f"{tar_dest.name}.sha256").write_text(
                            f"{digest}  {tar_dest.name}\n", encoding="utf-8"
                        )
                    archived_versions.add(ver)
                shutil.rmtree(item, ignore_errors=True)

    # 2. Move any loose files in release/ root: older versions -> previous/<ver>/, current version -> mac/ or windows/
    legacy_sh = release_dir / "install.sh"
    if legacy_sh.is_file():
        moved_files.append("install.sh")
        if not dry_run:
            legacy_target = previous_dir / "1.7.0"
            legacy_target.mkdir(parents=True, exist_ok=True)
            shutil.move(str(legacy_sh), str(legacy_target / "install.sh"))
            archived_versions.add("1.7.0")

    for item in sorted(release_dir.iterdir()):
        if not item.is_file() or item.name in ("README.md", "AGENTS.md", "CHECKSUMS.sha256", ".DS_Store", ".gitkeep"):
            continue
        m_file = version_file_re.search(item.name)
        if m_file:
            ver = m_file.group(1)
            if ver != current_version:
                moved_files.append(item.name)
                archived_versions.add(ver)
                if not dry_run:
                    ver_prev = previous_dir / ver
                    ver_prev.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(item), str(ver_prev / item.name))
                    for bin_name in (
                        "hath0r-darwin-arm64",
                        "hath0r-darwin-x86_64",
                        "hath0r-linux-arm64",
                        "hath0r-linux-x86_64",
                        "hath0r-windows-x64.cmd",
                    ):
                        src_bin = release_dir / bin_name
                        dst_bin = ver_prev / bin_name
                        if src_bin.is_file() and not dst_bin.is_file():
                            shutil.copy2(src_bin, dst_bin)
            else:
                moved_files.extend(_route_artifact_to_platform_folders(item, release_dir, current_version, dry_run))
        else:
            moved_files.extend(_route_artifact_to_platform_folders(item, release_dir, current_version, dry_run))

    # 3. Inspect release/mac, release/windows, release/vscode for any older-version items and move to previous/<ver>/<platform>/
    for plat in PLATFORM_FOLDERS:
        plat_dir = release_dir / plat
        if not plat_dir.is_dir():
            continue
        all_plat_files = [f for f in plat_dir.rglob("*") if f.is_file() and f.name not in (".DS_Store", ".gitkeep")]
        older_plat_ver = detect_previous_version(all_plat_files, exclude_version=current_version)
        if older_plat_ver and older_plat_ver != current_version:
            archived_versions.add(older_plat_ver)
            moved_files.append(f"{plat}/*->previous/{older_plat_ver}/{plat}/")
            if not dry_run:
                dest_plat_prev = previous_dir / older_plat_ver / plat
                dest_plat_prev.parent.mkdir(parents=True, exist_ok=True)
                if dest_plat_prev.exists():
                    shutil.rmtree(dest_plat_prev, ignore_errors=True)
                shutil.copytree(plat_dir, dest_plat_prev, dirs_exist_ok=True)
                for child in plat_dir.iterdir():
                    if child.is_dir():
                        shutil.rmtree(child, ignore_errors=True)
                    elif child.name not in (".DS_Store", ".gitkeep"):
                        child.unlink(missing_ok=True)

    if previous_dir.is_dir():
        for sub in previous_dir.iterdir():
            if sub.is_dir():
                archived_versions.add(sub.name)

    if not dry_run:
        for ver in sorted(archived_versions):
            ver_prev = previous_dir / ver
            if ver_prev.is_dir():
                generate_checksums(ver_prev)

    return {
        "archived_versions": sorted(archived_versions),
        "removed_temp_dirs": removed_temp_dirs,
        "moved_files": moved_files,
    }


def rotate_previous_release(
    release_dir: Path,
    previous_dir: Path,
    current_version: str,
    dry_run: bool = False,
    force_clear: bool = False,
) -> Optional[Path]:
    """Clear out `release/mac/`, `release/windows/`, `release/vscode/` (and root) into `release/previous/<version>/`."""
    release_dir.mkdir(parents=True, exist_ok=True)
    previous_dir.mkdir(parents=True, exist_ok=True)

    version_file_re = re.compile(r"[-_](\d+\.\d+\.\d+)(?:[-._]|$)")

    # Collect all artifacts in release/ root and in release/{mac,windows,vscode}
    root_artifacts = [
        item
        for item in sorted(release_dir.iterdir())
        if item.is_file() and item.name not in ("README.md", "AGENTS.md", "CHECKSUMS.sha256", ".DS_Store", ".gitkeep")
    ]
    platform_files: List[Path] = []
    for plat in PLATFORM_FOLDERS:
        pdir = release_dir / plat
        if pdir.is_dir():
            platform_files.extend(
                [f for f in pdir.rglob("*") if f.is_file() and f.name not in (".DS_Store", ".gitkeep")]
            )

    all_candidates = root_artifacts + platform_files
    if not all_candidates:
        cleanup_and_archive_release_dir(release_dir, previous_dir, current_version, dry_run=dry_run)
        return None

    older_ver = detect_previous_version(all_candidates, exclude_version=current_version)
    any_ver = detect_previous_version(all_candidates)

    if older_ver is not None:
        prev_ver = older_ver
    elif any_ver == current_version and not force_clear:
        # Active files in release/{mac,windows,vscode} are already at current_version
        cleanup_and_archive_release_dir(release_dir, previous_dir, current_version, dry_run=dry_run)
        return None
    elif any_ver is not None:
        prev_ver = any_ver
    else:
        prev_ver = "legacy"

    archive_target = previous_dir / prev_ver

    # 1. Rotate root files belonging to prev_ver (or unversioned) into archive_target
    to_move_root: List[Path] = []
    for art in root_artifacts:
        m = version_file_re.search(art.name)
        if m:
            if m.group(1) == prev_ver:
                to_move_root.append(art)
        else:
            to_move_root.append(art)

    if to_move_root:
        print(
            f"Rotating {len(to_move_root)} root release artifacts ({prev_ver}) into archive: {archive_target}",
            file=sys.stderr,
        )
        if not dry_run:
            archive_target.mkdir(parents=True, exist_ok=True)
            for art in to_move_root:
                shutil.move(str(art), str(archive_target / art.name))

    # 2. Clear out release/mac, release/windows, release/vscode into release/previous/<prev_ver>/{mac,windows,vscode}
    for plat in PLATFORM_FOLDERS:
        plat_dir = release_dir / plat
        if not plat_dir.is_dir():
            continue
        plat_items = [p for p in plat_dir.iterdir() if p.name not in (".DS_Store", ".gitkeep")]
        if not plat_items:
            continue
        plat_files = [f for f in plat_dir.rglob("*") if f.is_file() and f.name not in (".DS_Store", ".gitkeep")]
        plat_older = detect_previous_version(plat_files, exclude_version=current_version)
        target_ver_for_plat = plat_older or prev_ver
        if target_ver_for_plat != current_version or force_clear:
            dest_plat_archive = previous_dir / target_ver_for_plat / plat
            print(f"Clearing release/{plat} ({target_ver_for_plat}) -> {dest_plat_archive}", file=sys.stderr)
            if not dry_run:
                dest_plat_archive.parent.mkdir(parents=True, exist_ok=True)
                if dest_plat_archive.exists():
                    shutil.rmtree(dest_plat_archive, ignore_errors=True)
                shutil.copytree(plat_dir, dest_plat_archive, dirs_exist_ok=True)
                for item in plat_items:
                    if item.is_dir():
                        shutil.rmtree(item, ignore_errors=True)
                    else:
                        item.unlink(missing_ok=True)
                generate_checksums(previous_dir / target_ver_for_plat)

    if not dry_run and archive_target.is_dir():
        generate_checksums(archive_target)

    cleanup_and_archive_release_dir(release_dir, previous_dir, current_version, dry_run=dry_run)
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
        *pyinstaller_bundle_args(),
        str(entry_point),
    ]

    print(f"Building standalone binary {bin_name} -> {target_path}...", file=sys.stderr)
    if not dry_run:
        subprocess.run(cmd, cwd=cli_root, check=True)
        if work_dir.exists():
            shutil.rmtree(work_dir, ignore_errors=True)
        target_path.chmod(0o755)

    return target_path


def populate_platform_release_dirs(
    cli_root: Path,
    release_dir: Path,
    current_version: str,
    host_binary: Optional[Path] = None,
    dry_run: bool = False,
) -> Dict[str, str]:
    """Build and populate `release/mac/`, `release/windows/`, and `release/vscode/` with the new release artifacts."""
    mac_dir = release_dir / "mac"
    win_dir = release_dir / "windows"
    vscode_dir = release_dir / "vscode"

    if not dry_run:
        mac_dir.mkdir(parents=True, exist_ok=True)
        win_dir.mkdir(parents=True, exist_ok=True)
        vscode_dir.mkdir(parents=True, exist_ok=True)

        # 1. Build or locate current fileset tarball and place in both mac/ and windows/
        fileset_name = f"hath0r-fileset-{current_version}.tar.gz"
        fileset_sha_name = f"{fileset_name}.sha256"
        build_fileset_script = cli_root / "scripts" / "build_fileset.py"
        if not (mac_dir / fileset_name).is_file() and not (win_dir / fileset_name).is_file():
            if (release_dir / fileset_name).is_file():
                shutil.copy2(release_dir / fileset_name, mac_dir / fileset_name)
                shutil.move(str(release_dir / fileset_name), str(win_dir / fileset_name))
                if (release_dir / fileset_sha_name).is_file():
                    shutil.copy2(release_dir / fileset_sha_name, mac_dir / fileset_sha_name)
                    shutil.move(str(release_dir / fileset_sha_name), str(win_dir / fileset_sha_name))
            elif build_fileset_script.is_file():
                subprocess.run(
                    [sys.executable, str(build_fileset_script), "--out", str(mac_dir)],
                    cwd=cli_root,
                    check=True,
                )
        if (mac_dir / fileset_name).is_file() and not (win_dir / fileset_name).is_file():
            shutil.copy2(mac_dir / fileset_name, win_dir / fileset_name)
            if (mac_dir / fileset_sha_name).is_file():
                shutil.copy2(mac_dir / fileset_sha_name, win_dir / fileset_sha_name)
        elif (win_dir / fileset_name).is_file() and not (mac_dir / fileset_name).is_file():
            shutil.copy2(win_dir / fileset_name, mac_dir / fileset_name)
            if (win_dir / fileset_sha_name).is_file():
                shutil.copy2(win_dir / fileset_sha_name, mac_dir / fileset_sha_name)

        # 2. Copy Install Wizard scripts into mac/ and windows/
        wizard_py_src = cli_root / "scripts" / "install_hath0r.py"
        if wizard_py_src.is_file():
            for plat_dest in (mac_dir, win_dir):
                dst_py = plat_dest / "install_hath0r.py"
                shutil.copy2(wizard_py_src, dst_py)
                dst_py.chmod(0o755)
                dst_sh = plat_dest / "install-wizard.sh"
                if not dst_sh.is_file():
                    dst_sh.write_text(
                        '#!/usr/bin/env sh\nset -eu\nSCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"\nexec python3 "$SCRIPT_DIR/install_hath0r.py" "$@"\n',
                        encoding="utf-8",
                    )
                dst_sh.chmod(0o755)

        # 3. Ensure macOS binaries in release/mac/ and Windows command wrapper in release/windows/
        src_bin = host_binary if (host_binary and host_binary.is_file()) else None
        if src_bin is None:
            for cand in (
                mac_dir / "hath0r-darwin-arm64",
                release_dir / "hath0r-darwin-arm64",
                release_dir / "previous" / "1.21.0" / "hath0r-darwin-arm64",
            ):
                if cand.is_file():
                    src_bin = cand
                    break
        for darwin_name in ("hath0r-darwin-arm64", "hath0r-darwin-x86_64"):
            dest_darwin = mac_dir / darwin_name
            if not dest_darwin.is_file() and src_bin and src_bin.is_file():
                shutil.copy2(src_bin, dest_darwin)
                dest_darwin.chmod(0o755)

        win_cmd = win_dir / "hath0r-windows-x64.cmd"
        if not win_cmd.is_file():
            win_cmd.write_text("@echo off\r\npython -m hath0r_cli.cli %*\r\n", encoding="utf-8")

    # 4. Build macOS .dmg into release/mac/ and Windows .exe into release/windows/
    try:
        src_dir = cli_root / "src"
        if str(src_dir) not in sys.path:
            sys.path.insert(0, str(src_dir))
        from hath0r_cli.bots.install_wizard_bot import InstallWizardBot

        bot = InstallWizardBot(cwd=cli_root)
        bot.build_macos_dmg(out_dir=mac_dir, version=current_version, dry_run=dry_run)
        bot.build_windows_exe(out_dir=win_dir, version=current_version, dry_run=dry_run)
    except Exception as exc:
        print(f"Warning: Could not build native DMG/EXE installers: {exc}", file=sys.stderr)

    # 5. Build VSCode release into release/vscode/
    try:
        scripts_dir = cli_root / "scripts"
        if str(scripts_dir) not in sys.path:
            sys.path.insert(0, str(scripts_dir))
        from build_vscode_plugin import build_vscode_package

        if not dry_run and (cli_root / "packages" / "vscode-extension" / "package.json").is_file():
            build_vscode_package(release_dir=release_dir, version=current_version, use_vsce=False)
            for shared_name in (
                f"hath0r-fileset-{current_version}.tar.gz",
                f"hath0r-fileset-{current_version}.tar.gz.sha256",
                "install_hath0r.py",
                "install-wizard.sh",
            ):
                src_shared = mac_dir / shared_name
                if src_shared.is_file():
                    shutil.copy2(src_shared, vscode_dir / shared_name)
    except Exception as exc:
        print(f"Warning: Could not build VSCode extension package: {exc}", file=sys.stderr)

    # 6. Generate per-folder and root CHECKSUMS.sha256
    if not dry_run:
        for plat_dir in (mac_dir, win_dir, vscode_dir):
            if plat_dir.is_dir():
                generate_checksums(plat_dir)
        generate_checksums(release_dir)

    return {
        "mac_dir": str(mac_dir),
        "windows_dir": str(win_dir),
        "vscode_dir": str(vscode_dir),
    }


def sync_to_framework(
    cli_release_dir: Path,
    framework_release_dir: Path,
    current_version: Optional[str] = None,
    dry_run: bool = False,
) -> bool:
    """Synchronize `release/{mac,windows,vscode,previous}` and root docs to the Framework repository."""
    print(f"Synchronizing release folder: {cli_release_dir} -> {framework_release_dir}", file=sys.stderr)
    if not dry_run:
        framework_release_dir.mkdir(parents=True, exist_ok=True)
        framework_prev = framework_release_dir / "previous"
        framework_prev.mkdir(parents=True, exist_ok=True)

        if current_version:
            rotate_previous_release(
                framework_release_dir,
                framework_prev,
                current_version=current_version,
                dry_run=dry_run,
            )
            cleanup_and_archive_release_dir(
                framework_release_dir,
                framework_prev,
                current_version=current_version,
                dry_run=dry_run,
            )

        # Remove any stale loose binaries in framework_release_dir root so only README/AGENTS/CHECKSUMS remain at root
        for item in list(framework_release_dir.iterdir()):
            if item.is_file() and item.name not in ("README.md", "AGENTS.md", "CHECKSUMS.sha256", ".DS_Store", ".gitkeep"):
                item.unlink(missing_ok=True)

        # Copy root documentation & checksum files from CLI release/
        for item in cli_release_dir.iterdir():
            if item.is_file() and item.name in ("README.md", "CHECKSUMS.sha256"):
                shutil.copy2(item, framework_release_dir / item.name)

        # Sync mac/, windows/, vscode/ platform directories
        for plat in PLATFORM_FOLDERS:
            src_plat = cli_release_dir / plat
            dst_plat = framework_release_dir / plat
            if src_plat.is_dir():
                if dst_plat.exists():
                    shutil.rmtree(dst_plat, ignore_errors=True)
                shutil.copytree(src_plat, dst_plat, dirs_exist_ok=True)

        # Sync previous archive directories (including previous/README.md)
        cli_prev = cli_release_dir / "previous"
        if cli_prev.exists():
            prev_readme = cli_prev / "README.md"
            if prev_readme.is_file():
                shutil.copy2(prev_readme, framework_prev / "README.md")
            for sub in cli_prev.iterdir():
                if sub.is_dir():
                    dest_sub = framework_prev / sub.name
                    shutil.copytree(sub, dest_sub, dirs_exist_ok=True)
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
    """Execute complete release rotation (`mac`, `windows`, `vscode` -> `previous/`), build, checksumming, and Framework sync."""
    release_dir = (out_dir or (cli_root / "release")).resolve()
    prev_dir = (previous_dir or (release_dir / "previous")).resolve()
    current_ver = read_version(cli_root)

    if checksums_only:
        archived_path = None
        if rotate:
            archived_path = rotate_previous_release(release_dir, prev_dir, current_ver, dry_run=dry_run)
        cleanup_info = cleanup_and_archive_release_dir(release_dir, prev_dir, current_ver, dry_run=dry_run)
        platform_dirs = populate_platform_release_dirs(cli_root, release_dir, current_ver, dry_run=dry_run)
        chk = generate_checksums(release_dir) if not dry_run else (release_dir / "CHECKSUMS.sha256")
        if not dry_run and prev_dir.exists():
            for sub in prev_dir.iterdir():
                if sub.is_dir():
                    generate_checksums(sub)
        if sync_framework:
            fw_target = framework_release_dir or (cli_root.parent / "hath0r-framework" / "release")
            if fw_target.parent.is_dir():
                sync_to_framework(release_dir, fw_target, current_version=current_ver, dry_run=dry_run)
        return {
            "success": True,
            "checksums": str(chk),
            "version": current_ver,
            "platform_dirs": platform_dirs,
            "archived_path": str(archived_path) if archived_path else None,
            "archived_versions": cleanup_info.get("archived_versions", []),
        }

    # Step 1: Clear out release/{mac,windows,vscode} into release/previous/<version>/
    archived_path = None
    if rotate:
        archived_path = rotate_previous_release(
            release_dir, prev_dir, current_ver, dry_run=dry_run, force_clear=True
        )
    cleanup_and_archive_release_dir(release_dir, prev_dir, current_ver, dry_run=dry_run)

    # Step 2: Build standalone host binary into release/mac (or release/windows)
    mac_dir = release_dir / "mac"
    mac_dir.mkdir(parents=True, exist_ok=True)
    host_bin = build_pyinstaller_binary(cli_root, mac_dir, dry_run=dry_run)

    # Step 3: Populate release/mac, release/windows, and release/vscode with the new releases
    platform_dirs = populate_platform_release_dirs(
        cli_root, release_dir, current_ver, host_binary=host_bin, dry_run=dry_run
    )

    # Step 4: Calculate root release checksums
    if not dry_run:
        generate_checksums(release_dir)

    # Step 5: Synchronize with Framework release folder
    framework_synced = False
    if sync_framework:
        fw_target = framework_release_dir or (cli_root.parent / "hath0r-framework" / "release")
        framework_synced = sync_to_framework(release_dir, fw_target, current_version=current_ver, dry_run=dry_run)

    return {
        "success": True,
        "version": current_ver,
        "release_dir": str(release_dir),
        "platform_dirs": platform_dirs,
        "previous_dir": str(prev_dir),
        "archived_path": str(archived_path) if archived_path else None,
        "framework_synced": framework_synced,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Hath0r CLI release builder and rotator")
    parser.add_argument(
        "--cli-root", type=Path, default=Path(__file__).resolve().parents[1], help="Root directory of HATH0R-CLI"
    )
    parser.add_argument("--out-dir", type=Path, default=None, help="Output directory for release artifacts")
    parser.add_argument("--previous-dir", type=Path, default=None, help="Directory for previous version archives")
    parser.add_argument("--framework-dir", type=Path, default=None, help="Target Framework release directory")
    parser.add_argument("--no-rotate", action="store_true", help="Do not rotate existing release artifacts")
    parser.add_argument("--no-sync-framework", action="store_true", help="Do not sync artifacts to Framework repo")
    parser.add_argument("--checksums-only", action="store_true", help="Only regenerate checksums and sync")
    parser.add_argument("--dry-run", action="store_true", help="Print actions without modifying files")
    args = parser.parse_args()

    res = execute_release_build(
        cli_root=args.cli_root,
        out_dir=args.out_dir,
        previous_dir=args.previous_dir,
        framework_release_dir=args.framework_dir,
        rotate=not args.no_rotate,
        sync_framework=not args.no_sync_framework,
        checksums_only=args.checksums_only,
        dry_run=args.dry_run,
    )
    print(f"Release workflow complete: {res}")


if __name__ == "__main__":
    main()
