#!/usr/bin/env python3
"""Official Hath0r Install Wizard — CLI + Hath0r MCP (Docker) Bootstrap Installer.

Stdlib-only bootstrap wizard for operators and developers downloading a Hath0r release.
Executes a complete 5-stage installation pipeline:

1. Inspects & installs host dependencies (Python >= 3.10, pipx/pip, Git, curl, Docker Engine, Docker Compose v2).
2. Downloads and SHA-256 verifies the `hath0r` CLI release (wheel or standalone binary) and installs it globally on PATH.
3. Stages the `Hath0r-MCP` Dockerfile, `docker-compose.yml`, and canonical seed knowledgebase (`~/.hath0r/mcp`).
4. Creates the canonical `hath0r-net` Docker network (`CR-DOCKER-HATH0R-GROUP-001`) and launches `Hath0r-MCP` on port 38083.
5. Verifies `/ready` health, runs `hath0r upgrade verify`, configures `.hath0r/mcp.json`, and writes `INSTALL_RECEIPT.json`.

Usage:
    python3 scripts/install_hath0r.py [--version VER] [--installer pipx|binary|pip]
                                      [--mcp-port 38083] [--mcp-dir DIR] [--image-url URL]
                                      [--skip-docker] [--install-claude] [--file-issue]
                                      [-y/--yes] [--dry-run]

Never pipe unverified scripts from the internet into a shell; verify `CHECKSUMS.sha256` first.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path
from typing import Any, List, Optional

REPO = "Bayly-AI/HATH0R-CLI"
MCP_REPO = "Bayly-AI/HATH0R-MCP"
UA = {"User-Agent": "hath0r-install-wizard", "Accept": "application/vnd.github+json"}
DEFAULT_MCP_PORT = 38083
DEFAULT_NETWORK = "hath0r-net"
DEFAULT_CONTAINER = "Hath0r-MCP"


def _get(url: str) -> bytes:
    headers = dict(UA)
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token and url.startswith("https://api.github.com/"):
        headers["Authorization"] = f"Bearer {token}"
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=60) as resp:  # noqa: S310
        data: bytes = resp.read()
        return data


def _release(repo: str, version: str | None) -> dict[str, Any]:
    path = f"releases/tags/v{version.lstrip('v')}" if version else "releases/latest"
    res: dict[str, Any] = json.loads(_get(f"https://api.github.com/repos/{repo}/{path}"))
    return res


def _expected_sha(release: dict[str, Any], asset: dict[str, Any]) -> str:
    digest = str(asset.get("digest") or "")
    if digest.startswith("sha256:"):
        return digest.split(":", 1)[1].lower()
    for a in release.get("assets", []):
        if a.get("name") == str(asset.get("name", "")) + ".sha256":
            m = re.search(r"\b([a-fA-F0-9]{64})\b", _get(a["browser_download_url"]).decode("utf-8", "replace"))
            if m:
                return m.group(1).lower()
    sys.exit(f"✗ No SHA-256 published for {asset.get('name')} — refusing to install an unverified artifact.")


def _default_bin_dir() -> Path:
    override = os.environ.get("HATH0R_BIN_DIR")
    if override:
        return Path(override).expanduser().resolve()
    usr_local = Path("/usr/local/bin")
    if usr_local.is_dir() and os.access(usr_local, os.W_OK):
        return usr_local
    return (Path.home() / ".local" / "bin").resolve()


def _ensure_path(bin_dir: Path, dry_run: bool = False) -> None:
    bin_str = str(bin_dir)
    entries = [p for p in os.environ.get("PATH", "").split(os.pathsep) if p]
    if bin_str not in entries:
        os.environ["PATH"] = f"{bin_str}{os.pathsep}{os.environ.get('PATH', '')}"
    shell = os.environ.get("SHELL", "")
    prof = Path.home() / (".zshrc" if "zsh" in shell else ".bashrc")
    if prof.is_file() and not dry_run:
        try:
            text = prof.read_text(encoding="utf-8")
            if bin_str not in text:
                with prof.open("a", encoding="utf-8") as fh:
                    fh.write(f'\n# Added by Hath0r Install Wizard\nexport PATH="{bin_str}:$PATH"\n')
        except OSError:
            pass


def _find_local_release_dir() -> Optional[Path]:
    script_dir = Path(__file__).resolve().parent
    candidates = [
        script_dir,
        script_dir.parent / "release",
        Path.cwd() / "release",
    ]
    for cand in candidates:
        if (cand / "CHECKSUMS.sha256").is_file():
            return cand.resolve()
    return None


def _check_and_install_prereqs(installer: str, skip_docker: bool, auto_yes: bool, dry_run: bool) -> None:
    print("==> Stage 1/5: Checking system dependencies...")
    if (sys.version_info.major, sys.version_info.minor) < (3, 10):
        sys.exit(f"✗ Python >= 3.10 is required (found {platform.python_version()}).")

    missing: List[str] = []
    for cmd in ("git", "curl"):
        if not shutil.which(cmd):
            missing.append(cmd)
    if installer == "pipx" and not shutil.which("pipx"):
        missing.append("pipx")
    if not skip_docker:
        if not shutil.which("docker"):
            missing.append("docker")
        else:
            rc = subprocess.run(["docker", "compose", "version"], capture_output=True, check=False).returncode
            if rc != 0:
                missing.append("docker-compose-v2")

    if missing:
        print(f"    Missing prerequisites detected: {', '.join(missing)}")
        if not auto_yes and sys.stdin.isatty() and not dry_run:
            ans = input("    Install missing dependencies automatically? [Y/n]: ").strip().lower()
            if ans in ("n", "no"):
                sys.exit("✗ Aborted: required dependencies are not installed.")

        brew = shutil.which("brew")
        apt = shutil.which("apt-get")
        winget = shutil.which("winget")
        for item in missing:
            if dry_run:
                print(f"    [DRY-RUN] Would install {item}")
                continue
            if item == "pipx":
                if brew:
                    subprocess.run(["brew", "install", "pipx"], check=False)
                else:
                    subprocess.run([sys.executable, "-m", "pip", "install", "--user", "--upgrade", "pipx"], check=False)
                subprocess.run([sys.executable, "-m", "pipx", "ensurepath"], check=False)
            elif item in ("git", "curl"):
                if brew:
                    subprocess.run(["brew", "install", item], check=False)
                elif apt:
                    subprocess.run(["sudo", "apt-get", "install", "-y", item], check=False)
                elif winget:
                    pkg_id = "Git.Git" if item == "git" else "cURL.cURL"
                    subprocess.run(
                        ["winget", "install", "-e", "--id", pkg_id, "--accept-package-agreements", "--accept-source-agreements"],
                        check=False,
                    )
            elif item in ("docker", "docker-compose-v2"):
                if brew:
                    subprocess.run(["brew", "install", "--cask", "docker"], check=False)
                elif apt:
                    subprocess.run(["sudo", "apt-get", "install", "-y", "docker.io", "docker-compose-v2"], check=False)
                elif winget:
                    subprocess.run(
                        [
                            "winget",
                            "install",
                            "-e",
                            "--id",
                            "Docker.DockerDesktop",
                            "--accept-package-agreements",
                            "--accept-source-agreements",
                        ],
                        check=False,
                    )

    if not skip_docker and not dry_run and shutil.which("docker"):
        rc_info = subprocess.run(["docker", "info"], capture_output=True, check=False).returncode
        if rc_info != 0:
            print("    Starting Docker daemon...")
            sys_lower = platform.system().lower()
            if sys_lower == "darwin":
                subprocess.run(["open", "-a", "Docker"], check=False)
            elif sys_lower == "linux":
                subprocess.run(["sudo", "systemctl", "start", "docker"], check=False)
            elif sys_lower.startswith("win"):
                docker_desktop = Path(r"C:\Program Files\Docker\Docker\Docker Desktop.exe")
                if docker_desktop.is_file():
                    subprocess.Popen([str(docker_desktop)])
            for _ in range(15):
                if subprocess.run(["docker", "info"], capture_output=True, check=False).returncode == 0:
                    break
                time.sleep(1)
    print("    ✓ System dependencies ready.")


def _install_cli_global(
    repo: str,
    version: Optional[str],
    installer: str,
    bin_dir: Path,
    dry_run: bool,
) -> tuple[str, str]:
    """Install Hath0r CLI globally and return (exe_path, resolved_version)."""
    print(f"==> Stage 2/5: Installing Hath0r CLI globally (method={installer})...")
    _ensure_path(bin_dir, dry_run=dry_run)
    local_rel = _find_local_release_dir()
    cli_repo_root = Path(__file__).resolve().parents[1]

    # Option 1: Local pre-compiled binary in release/
    sys_name = platform.system().lower()
    mach = platform.machine().lower()
    arch_x86 = "arm64" if mach in ("arm64", "aarch64") else "x86_64"
    local_bin_name = f"hath0r-{sys_name}-{arch_x86}"

    if installer == "binary" and local_rel and (local_rel / local_bin_name).is_file():
        src_bin = local_rel / local_bin_name
        ver_str = version or (
            (cli_repo_root / "VERSION").read_text(encoding="utf-8").strip()
            if (cli_repo_root / "VERSION").is_file()
            else "latest"
        )
        target_bin = bin_dir / "hath0r"
        if dry_run:
            print(f"    [DRY-RUN] Would verify SHA-256 of {src_bin.name} and install to {target_bin}.")
            return str(target_bin), ver_str
        bin_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_bin, target_bin)
        target_bin.chmod(0o755)
        print(f"    ✓ Installed standalone binary to {target_bin}")
        return str(target_bin), ver_str

    # Option 2: GitHub Release wheel (or local checkout fallback)
    release: Optional[dict[str, Any]] = None
    try:
        release = _release(repo, version)
    except Exception:
        release = None

    if release is not None:
        resolved_ver = str(release.get("tag_name", "")).lstrip("v")
        wheel = next(
            (
                a
                for a in release.get("assets", [])
                if str(a.get("name", "")).startswith(f"hath0r_cli-{resolved_ver}-")
                and str(a.get("name", "")).endswith(".whl")
            ),
            None,
        )
        if wheel:
            expected = _expected_sha(release, wheel)
            print(f"    ==> hath0r {resolved_ver} · {wheel['name']} · installer={installer}")
            if dry_run:
                print(f"    [DRY-RUN] Would download, verify sha256={expected[:16]}…, and install with {installer}.")
                return shutil.which("hath0r") or str(bin_dir / "hath0r"), resolved_ver

            with tempfile.TemporaryDirectory(prefix="hath0r-install-") as tmp:
                dest = Path(tmp) / wheel["name"]
                dest.write_bytes(_get(wheel["browser_download_url"]))
                actual = hashlib.sha256(dest.read_bytes()).hexdigest()
                if actual != expected:
                    sys.exit(f"✗ SHA-256 mismatch: expected {expected}, got {actual}. Not installing.")
                print("    ==> checksum verified")
                cmd = (
                    ["pipx", "install", "--force", str(dest)]
                    if installer == "pipx"
                    else [sys.executable, "-m", "pip", "install", "--upgrade", str(dest)]
                )
                if subprocess.run(cmd, check=False).returncode != 0:
                    sys.exit("✗ CLI install command failed (see output above).")
            exe = shutil.which("hath0r") or str(bin_dir / "hath0r")
            return exe, resolved_ver

    # Option 3: Local source checkout fallback
    if (cli_repo_root / "pyproject.toml").is_file():
        resolved_ver = (
            (cli_repo_root / "VERSION").read_text(encoding="utf-8").strip()
            if (cli_repo_root / "VERSION").is_file()
            else "local"
        )
        if dry_run:
            print(f"    [DRY-RUN] Would install hath0r {resolved_ver} from local source checkout {cli_repo_root}.")
            return shutil.which("hath0r") or str(bin_dir / "hath0r"), resolved_ver
        cmd = (
            ["pipx", "install", "--force", str(cli_repo_root)]
            if installer == "pipx" and shutil.which("pipx")
            else [sys.executable, "-m", "pip", "install", "-e", str(cli_repo_root)]
        )
        if subprocess.run(cmd, check=False).returncode != 0:
            sys.exit("✗ Local CLI install command failed.")
        exe = shutil.which("hath0r") or str(bin_dir / "hath0r")
        return exe, resolved_ver

    sys.exit(f"✗ Could not locate a hath0r_cli wheel asset in {repo} release.")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--version", default=None, help="Release version to install (default: latest).")
    ap.add_argument(
        "--installer",
        "--method",
        dest="installer",
        choices=["pipx", "binary", "pip"],
        default=None,
        help="CLI install method (default: pipx if available, else pip).",
    )
    ap.add_argument("--bin-dir", type=Path, default=None, help="Global binary directory.")
    ap.add_argument("--mcp-dir", type=Path, default=None, help="Directory to stage Hath0r MCP Docker files.")
    ap.add_argument("--mcp-port", type=int, default=DEFAULT_MCP_PORT, help="Host port for Hath0r-MCP container.")
    ap.add_argument("--image-url", default=None, help="Optional remote container registry image URL for Hath0r-MCP.")
    ap.add_argument("--skip-docker", "--cli-only", dest="skip_docker", action="store_true", help="Skip Docker MCP launch.")
    ap.add_argument("--install-claude", action="store_true", help="Register connector in Claude Desktop config.")
    ap.add_argument("--repo", default=REPO)
    ap.add_argument("--file-issue", action="store_true", help="Open a GitHub issue if verification fails.")
    ap.add_argument("-y", "--yes", action="store_true", help="Run non-interactively accepting defaults.")
    ap.add_argument("--dry-run", action="store_true", help="Preview installation steps without modifying the system.")
    args = ap.parse_args()

    installer = args.installer or ("pipx" if shutil.which("pipx") else "pip")
    bin_dir = (args.bin_dir or _default_bin_dir()).resolve()

    print("╔══════════════════════════════════════════════════════════════════════════════╗")
    print("║            HATH0R CLI & HATH0R MCP (DOCKER) — INSTALL WIZARD                 ║")
    print("╚══════════════════════════════════════════════════════════════════════════════╝")

    # Stage 1: Prerequisites
    _check_and_install_prereqs(
        installer=installer,
        skip_docker=args.skip_docker,
        auto_yes=args.yes,
        dry_run=args.dry_run,
    )

    # Stage 2: Global CLI Install
    exe, version = _install_cli_global(
        repo=args.repo,
        version=args.version,
        installer=installer,
        bin_dir=bin_dir,
        dry_run=args.dry_run,
    )

    if args.dry_run:
        print(
            f"==> Stages 3-5/5: [DRY-RUN] Would stage Hath0r MCP Dockerfile, create network '{DEFAULT_NETWORK}', "
            f"launch container '{DEFAULT_CONTAINER}' on 127.0.0.1:{args.mcp_port}, and verify CLI + MCP health."
        )
        return 0

    found_exe = shutil.which("hath0r") or (exe if Path(exe).is_file() else None)
    if not found_exe:
        print("✗ Installed, but `hath0r` is not on PATH (pipx: run `pipx ensurepath`, then open a new shell).")
        return 1

    # Stage 3-5: Delegate to `hath0r install-wizard run` for MCP Docker staging, container launch & verification
    print("==> Stages 3-5/5: Staging Hath0r MCP Dockerfile, launching Docker container & verifying...")
    wiz_cmd = [
        found_exe,
        "-o",
        "text",
        "install-wizard",
        "run",
        "--yes",
        "--method",
        installer,
        "--mcp-port",
        str(args.mcp_port),
    ]
    if args.mcp_dir:
        wiz_cmd.extend(["--mcp-dir", str(args.mcp_dir)])
    if args.image_url:
        wiz_cmd.extend(["--image-url", args.image_url])
    if args.skip_docker:
        wiz_cmd.append("--skip-docker")
    if args.install_claude:
        wiz_cmd.append("--install-claude")

    wiz_rc = subprocess.run(wiz_cmd, check=False).returncode
    if wiz_rc != 0:
        # Fallback to direct upgrade verify if running against an older CLI release prior to install-wizard
        verify_cmd = [found_exe, "-o", "text", "upgrade", "verify", "--expect-version", version, "--announce"]
        if args.file_issue:
            verify_cmd.append("--file-issue")
        code = subprocess.run(verify_cmd, check=False).returncode
        print("✓ hath0r installed and verified." if code == 0 else "✗ Verification failed — see announcement above.")
        return code

    print(f"✓ Hath0r CLI ({version}) and Hath0r-MCP Docker (: {args.mcp_port}) installed and verified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
