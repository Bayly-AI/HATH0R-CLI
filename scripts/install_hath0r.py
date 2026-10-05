#!/usr/bin/env python3
"""Verified first-time installer for the hath0r CLI (stdlib only).

Downloads the release wheel from GitHub Releases, verifies its SHA-256 against the digest
GitHub publishes for the asset (or the ``.sha256`` sidecar), installs it with pipx (preferred)
or pip, then hands over to the Upgrade Bot's verifier:

    hath0r upgrade verify --announce [--file-issue]

so a fresh install is tested — and failures announced — exactly like an upgrade.
After this first install, keep the CLI current with ``hath0r upgrade run`` (or the
``upgrade-factory`` nightly schedule).

Usage:
    python3 scripts/install_hath0r.py [--version 0.9.0] [--installer pipx|pip] [--file-issue] [--dry-run]

Never pipe this into a shell from an unverified URL; run it from a checked-out copy.
See docs/hathor-guide-049-automated-upgrade-install-20261005.md.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

REPO = "Bayly-AI/HATH0R-CLI"
UA = {"User-Agent": "hath0r-installer", "Accept": "application/vnd.github+json"}


def _get(url: str) -> bytes:
    headers = dict(UA)
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token and url.startswith("https://api.github.com/"):
        headers["Authorization"] = f"Bearer {token}"
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=60) as resp:  # noqa: S310
        data: bytes = resp.read()
        return data


def _release(repo: str, version: str | None) -> dict:
    path = f"releases/tags/v{version.lstrip('v')}" if version else "releases/latest"
    return json.loads(_get(f"https://api.github.com/repos/{repo}/{path}"))


def _expected_sha(release: dict, asset: dict) -> str:
    digest = asset.get("digest") or ""
    if digest.startswith("sha256:"):
        return digest.split(":", 1)[1].lower()
    for a in release.get("assets", []):
        if a["name"] == asset["name"] + ".sha256":
            m = re.search(r"\b([a-fA-F0-9]{64})\b", _get(a["browser_download_url"]).decode("utf-8", "replace"))
            if m:
                return m.group(1).lower()
    sys.exit(f"✗ No SHA-256 published for {asset['name']} — refusing to install an unverified artifact.")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--version", default=None, help="Release to install (default: latest).")
    ap.add_argument("--installer", choices=["pipx", "pip"], default=None, help="Default: pipx if available, else pip.")
    ap.add_argument("--repo", default=REPO)
    ap.add_argument("--file-issue", action="store_true", help="Open a GitHub issue if verification fails.")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    installer = args.installer or ("pipx" if shutil.which("pipx") else "pip")
    release = _release(args.repo, args.version)
    version = release["tag_name"].lstrip("v")
    wheel = next(
        (
            a
            for a in release.get("assets", [])
            if a["name"].startswith(f"hath0r_cli-{version}-") and a["name"].endswith(".whl")
        ),
        None,
    )
    if not wheel:
        sys.exit(f"✗ Release {release['tag_name']} has no hath0r_cli wheel asset.")
    expected = _expected_sha(release, wheel)
    print(f"==> hath0r {version} · {wheel['name']} · installer={installer}")
    if args.dry_run:
        print(f"[DRY-RUN] Would download, verify sha256={expected[:16]}…, install with {installer}, then verify.")
        return 0

    with tempfile.TemporaryDirectory(prefix="hath0r-install-") as tmp:
        dest = Path(tmp) / wheel["name"]
        dest.write_bytes(_get(wheel["browser_download_url"]))
        actual = hashlib.sha256(dest.read_bytes()).hexdigest()
        if actual != expected:
            sys.exit(f"✗ SHA-256 mismatch: expected {expected}, got {actual}. Not installing.")
        print("==> checksum verified")
        cmd = (
            ["pipx", "install", "--force", str(dest)]
            if installer == "pipx"
            else [sys.executable, "-m", "pip", "install", "--upgrade", str(dest)]
        )
        if subprocess.run(cmd, check=False).returncode != 0:
            sys.exit("✗ Install command failed (see output above).")

    exe = shutil.which("hath0r")
    if not exe:
        print("✗ Installed, but `hath0r` is not on PATH (pipx: run `pipx ensurepath`, then open a new shell).")
        return 1
    print("==> verifying install with the Upgrade Bot")
    verify = [exe, "-o", "text", "upgrade", "verify", "--expect-version", version, "--announce"]
    if args.file_issue:
        verify.append("--file-issue")
    code = subprocess.run(verify, check=False).returncode
    print("✓ hath0r installed and verified." if code == 0 else "✗ Verification failed — see the announcement above.")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
