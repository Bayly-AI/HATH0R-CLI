"""Upgrade & install bots for the HATH0R CLI.

Three cooperating bots manage an automated, self-verifying upgrade of the ``hath0r`` CLI:

- :class:`UpgradeBot` — detects how the CLI is installed (source checkout, pip, pipx or
  standalone binary), checks GitHub Releases for a newer version, downloads and
  checksum-verifies the artifact, snapshots the current install, installs the new version,
  and rolls back automatically when verification fails.
- :class:`UpgradeVerifierBot` — runs the post-install test suite against the *installed*
  CLI in a fresh subprocess (version match, command import scan, ``doctor`` regression
  check, and optionally the full unit-test suite for source checkouts).
- :class:`UpgradeAnnouncerBot` — reports the outcome: console summary, persisted report and
  history, spoken notification queue, and (opt-in) a de-duplicated GitHub issue describing
  what failed and how to fix it.

The module is deliberately stdlib-only so it keeps working when the CLI's optional
dependencies are broken — which is exactly the situation an upgrade bot must survive.

Governance: CR-CLI-FEATURE-STANDARD-001 · Bot spec: docs/governance/bot-specs/upgrade-bot-spec.md
"""

from __future__ import annotations

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
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

DEFAULT_REPO = "Bayly-AI/HATH0R-CLI"
DIST_NAME = "hath0r-cli"
PACKAGE_NAME = "hath0r_cli"
CANONICAL_SOURCE_BRANCHES = ("development", "master")
INSTALL_METHODS = ("source", "pip", "pipx", "binary")
TEST_LEVELS = ("smoke", "full")
REPORT_SCHEMA = "hath0r.upgrade.report/1"
LAUNCHD_LABEL = "com.baylyai.hath0r.upgrade"

# Exit codes (contracts/exit-codes.yaml): 0 ok / no-op, 1 runtime failure (rolled back),
# 6 dependency unhealthy (failure AND rollback failed — install needs operator attention).
EXIT_OK = 0
EXIT_FAILED = 1
EXIT_ROLLBACK_FAILED = 6

Runner = Callable[..., Tuple[int, str, str]]
HttpGet = Callable[[str, Dict[str, str]], bytes]

_SEMVER_RE = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z.-]+))?(?:\+[0-9A-Za-z.-]+)?$")
_SHA256_RE = re.compile(r"\b([a-fA-F0-9]{64})\b")


# ── helpers ────────────────────────────────────────────────────────────────────


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_version(value: str) -> Tuple[int, int, int, Tuple[int, str]]:
    """Parse a SemVer string (optionally ``v``-prefixed) into a sortable key.

    Pre-releases sort *below* the matching release (``1.0.0-rc.1 < 1.0.0``).
    """
    m = _SEMVER_RE.match((value or "").strip())
    if not m:
        raise ValueError(f"Not a semantic version: {value!r}")
    major, minor, patch, pre = m.groups()
    pre_key = (1, "") if not pre else (0, pre)
    return int(major), int(minor), int(patch), pre_key


def compare_versions(a: str, b: str) -> int:
    """Return -1, 0 or 1 when ``a`` is older than, equal to, or newer than ``b``."""
    ka, kb = parse_version(a), parse_version(b)
    return (ka > kb) - (ka < kb)


def normalize_version(value: str) -> str:
    return (value or "").strip().lstrip("vV")


def _child_env() -> Dict[str, str]:
    """Environment for child processes.

    PYTHONPATH/PYTHONHOME are dropped so verification exercises the *installed* package,
    not whatever source tree happens to be on the parent's import path.
    """
    env = {k: v for k, v in os.environ.items() if k not in ("PYTHONPATH", "PYTHONHOME")}
    env["HATH0R_UPGRADE_CHILD"] = "1"
    return env


def _last_line(text: str) -> str:
    """Last non-empty line of command output (the exception line of a traceback)."""
    lines = [ln.strip() for ln in (text or "").splitlines() if ln.strip()]
    return lines[-1] if lines else ""


def default_runner(args: List[str], cwd: Optional[Path] = None, timeout: int = 900) -> Tuple[int, str, str]:
    """Run a command without a shell; never raises."""
    try:
        proc = subprocess.run(
            args,
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
            env=_child_env(),
        )
        return proc.returncode, (proc.stdout or "").strip(), (proc.stderr or "").strip()
    except subprocess.TimeoutExpired:
        return 124, "", f"Command timed out after {timeout}s: {' '.join(args[:4])}"
    except FileNotFoundError as exc:
        return 127, "", f"Command not found: {exc}"
    except Exception as exc:  # pragma: no cover - defensive
        return 1, "", str(exc)


def default_http_get(url: str, headers: Dict[str, str]) -> bytes:
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=60) as resp:  # noqa: S310 - https GitHub URLs only
        data: bytes = resp.read()
        return data


def upgrade_home() -> Path:
    """State directory for reports, history, backups and the run lock."""
    override = os.environ.get("HATH0R_UPGRADE_HOME")
    return Path(override).expanduser() if override else Path.home() / ".hath0r" / "upgrade"


def platform_tag() -> Optional[str]:
    """Release-asset platform tag for standalone binaries (``hath0r-<ver>-<tag>``)."""
    system = platform.system().lower()
    machine = platform.machine().lower()
    arch = {"arm64": "arm64", "aarch64": "arm64", "x86_64": "x64", "amd64": "x64"}.get(machine)
    if system in ("darwin", "linux") and arch:
        return f"{system}-{arch}"
    return None


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class UpgradeError(Exception):
    """A failure at a named stage of the upgrade pipeline."""

    def __init__(self, stage: str, code: str, message: str, hint: str = "") -> None:
        super().__init__(message)
        self.stage = stage
        self.code = code
        self.message = message
        self.hint = hint

    def to_dict(self) -> Dict[str, Any]:
        return {"stage": self.stage, "code": self.code, "message": self.message, "hint": self.hint}


# ── data models ────────────────────────────────────────────────────────────────


@dataclass
class InstallInfo:
    """How and where the running CLI is installed."""

    method: str
    version: str
    python: str
    package_path: str = ""
    repo_root: str = ""
    branch: str = ""
    head_sha: str = ""
    binary_path: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v not in ("", None, {})}


@dataclass
class ReleaseInfo:
    """A published GitHub Release of the CLI."""

    tag: str
    version: str
    url: str = ""
    published_at: str = ""
    assets: List[Dict[str, Any]] = field(default_factory=list)

    def asset(self, name: str) -> Optional[Dict[str, Any]]:
        return next((a for a in self.assets if a.get("name") == name), None)

    def wheel(self) -> Optional[Dict[str, Any]]:
        prefix = f"{PACKAGE_NAME}-{self.version}-"
        return next((a for a in self.assets if a["name"].startswith(prefix) and a["name"].endswith(".whl")), None)

    def binary(self, tag: Optional[str]) -> Optional[Dict[str, Any]]:
        return self.asset(f"hath0r-{self.version}-{tag}") if tag else None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tag": self.tag,
            "version": self.version,
            "url": self.url,
            "published_at": self.published_at,
            "asset_names": [a.get("name") for a in self.assets],
        }


# ── UpgradeBot ─────────────────────────────────────────────────────────────────


@dataclass
class UpgradeBot:
    """Detects, downloads, verifies, installs and (on failure) rolls back CLI upgrades."""

    cwd: Path = field(default_factory=Path.cwd)
    repo: str = DEFAULT_REPO
    runner: Runner = field(default=default_runner, repr=False)
    http_get: HttpGet = field(default=default_http_get, repr=False)
    state_dir: Path = field(default_factory=upgrade_home)
    python: str = field(default_factory=lambda: sys.executable)

    # ── state files ──
    @property
    def report_file(self) -> Path:
        return self.state_dir / "last-run.json"

    @property
    def history_file(self) -> Path:
        return self.state_dir / "history.jsonl"

    @property
    def lock_file(self) -> Path:
        return self.state_dir / "upgrade.lock"

    @property
    def backup_dir(self) -> Path:
        return self.state_dir / "backups"

    # ── detection ──
    def detect_install(self) -> InstallInfo:
        """Work out whether this CLI runs from a source checkout, pip, pipx or a frozen binary."""
        if getattr(sys, "frozen", False):
            from hath0r_cli import __version__

            return InstallInfo(
                method="binary", version=__version__, python=self.python, binary_path=str(Path(sys.executable))
            )

        import hath0r_cli

        version = getattr(hath0r_cli, "__version__", "0.0.0")
        pkg_path = Path(hath0r_cli.__file__).resolve().parent
        info = InstallInfo(method="pip", version=version, python=self.python, package_path=str(pkg_path))

        repo_root = self._find_source_root(pkg_path)
        if repo_root is not None:
            info.method = "source"
            info.repo_root = str(repo_root)
            _, branch, _ = self.runner(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=repo_root, timeout=30)
            _, sha, _ = self.runner(["git", "rev-parse", "HEAD"], cwd=repo_root, timeout=30)
            info.branch, info.head_sha = branch.strip(), sha.strip()
            return info

        prefix = Path(sys.prefix).as_posix()
        if "/pipx/venvs/" in prefix or os.environ.get("PIPX_HOME", "\0") in prefix:
            info.method = "pipx"
        info.details["prefix"] = prefix
        return info

    @staticmethod
    def _find_source_root(pkg_path: Path) -> Optional[Path]:
        for parent in [pkg_path, *pkg_path.parents][:4]:
            pyproject = parent / "pyproject.toml"
            if (parent / ".git").exists() and pyproject.is_file():
                try:
                    if re.search(r'^name\s*=\s*"hath0r-cli"', pyproject.read_text(encoding="utf-8"), re.M):
                        return parent
                except OSError:
                    return None
        return None

    # ── release feed ──
    def _api_headers(self) -> Dict[str, str]:
        headers = {"Accept": "application/vnd.github+json", "User-Agent": "hath0r-upgrade-bot"}
        token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    def _github_json(self, path: str) -> Any:
        url = f"https://api.github.com/repos/{self.repo}/{path}"
        try:
            return json.loads(self.http_get(url, self._api_headers()).decode("utf-8"))
        except Exception as http_exc:
            # Fall back to the authenticated GitHub CLI (handles rate limits / private forks).
            code, out, err = self.runner(["gh", "api", f"repos/{self.repo}/{path}"], timeout=60)
            if code == 0 and out:
                return json.loads(out)
            raise UpgradeError(
                "check",
                "RELEASE_FEED_UNAVAILABLE",
                f"Could not read GitHub releases for {self.repo}: {http_exc}; gh fallback: {err or 'unavailable'}",
                "Check network access to api.github.com, or run `gh auth login` / set GITHUB_TOKEN.",
            ) from http_exc

    def fetch_release(self, version: Optional[str] = None) -> ReleaseInfo:
        path = f"releases/tags/v{normalize_version(version)}" if version else "releases/latest"
        data = self._github_json(path)
        tag = str(data.get("tag_name") or "")
        assets = [
            {
                "name": a.get("name", ""),
                "url": a.get("browser_download_url", ""),
                "size": a.get("size", 0),
                "digest": a.get("digest") or "",
            }
            for a in data.get("assets", [])
        ]
        return ReleaseInfo(
            tag=tag,
            version=normalize_version(tag),
            url=str(data.get("html_url") or ""),
            published_at=str(data.get("published_at") or ""),
            assets=assets,
        )

    def check(self, version: Optional[str] = None) -> Dict[str, Any]:
        """Compare the installed CLI with the latest (or a pinned) release. Read-only."""
        install = self.detect_install()
        try:
            release = self.fetch_release(version)
            cmp = compare_versions(release.version, install.version)
        except UpgradeError as exc:
            return {"success": False, "install": install.to_dict(), "error": exc.message, "failure": exc.to_dict()}
        except ValueError as exc:
            return {"success": False, "install": install.to_dict(), "error": str(exc)}
        return {
            "success": True,
            "install": install.to_dict(),
            "release": release.to_dict(),
            "current_version": install.version,
            "latest_version": release.version,
            "update_available": cmp > 0,
            "message": (
                f"Update available: {install.version} → {release.version} ({install.method} install)."
                if cmp > 0
                else f"hath0r {install.version} is up to date ({'target' if version else 'latest'} release {release.version})."
            ),
        }

    # ── download + checksum ──
    def _expected_sha256(self, release: ReleaseInfo, asset: Dict[str, Any]) -> str:
        digest = str(asset.get("digest") or "")
        if digest.startswith("sha256:"):
            return digest.split(":", 1)[1].lower()
        sidecar = release.asset(asset["name"] + ".sha256")
        if sidecar:
            text = self.http_get(sidecar["url"], {"User-Agent": "hath0r-upgrade-bot"}).decode("utf-8", "replace")
            m = _SHA256_RE.search(text)
            if m:
                return m.group(1).lower()
        raise UpgradeError(
            "download",
            "CHECKSUM_MISSING",
            f"No SHA-256 checksum published for {asset['name']}; refusing to install an unverified artifact.",
            "Publish a .sha256 sidecar (release.yml) or re-run the release so GitHub records asset digests.",
        )

    def download_verified(self, release: ReleaseInfo, asset: Dict[str, Any], dest_dir: Path) -> Dict[str, Any]:
        expected = self._expected_sha256(release, asset)
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / asset["name"]
        try:
            dest.write_bytes(self.http_get(asset["url"], {"User-Agent": "hath0r-upgrade-bot"}))
        except Exception as exc:
            raise UpgradeError(
                "download", "DOWNLOAD_FAILED", f"Download of {asset['name']} failed: {exc}", "Retry later."
            ) from exc
        actual = sha256_file(dest)
        if actual != expected:
            dest.unlink(missing_ok=True)
            raise UpgradeError(
                "download",
                "CHECKSUM_MISMATCH",
                f"SHA-256 mismatch for {asset['name']}: expected {expected}, got {actual}.",
                "Do not install. Re-download; if it persists the release asset may be corrupt or tampered with.",
            )
        return {"path": str(dest), "sha256": actual, "asset": asset["name"]}

    # ── locking ──
    def _acquire_lock(self) -> None:
        self.state_dir.mkdir(parents=True, exist_ok=True)
        if self.lock_file.exists():
            try:
                pid = int(self.lock_file.read_text().strip() or "0")
                os.kill(pid, 0)
                raise UpgradeError(
                    "preflight",
                    "UPGRADE_IN_PROGRESS",
                    f"Another upgrade is running (pid {pid}).",
                    f"Wait for it to finish, or delete {self.lock_file} if that process is gone.",
                )
            except (ValueError, ProcessLookupError, PermissionError):
                pass  # stale lock
        self.lock_file.write_text(str(os.getpid()))

    def _release_lock(self) -> None:
        try:
            self.lock_file.unlink(missing_ok=True)
        except OSError:
            pass

    # ── preflight / snapshot ──
    def preflight(self, install: InstallInfo, release: ReleaseInfo) -> Dict[str, Any]:
        if install.method == "source":
            root = Path(install.repo_root)
            _, dirty, _ = self.runner(["git", "status", "--porcelain", "--untracked-files=no"], cwd=root, timeout=60)
            if dirty.strip():
                raise UpgradeError(
                    "preflight",
                    "SOURCE_TREE_DIRTY",
                    f"Source checkout {root} has uncommitted changes.",
                    "Commit or stash your changes, then re-run `hath0r upgrade run`.",
                )
            if install.branch not in CANONICAL_SOURCE_BRANCHES:
                raise UpgradeError(
                    "preflight",
                    "SOURCE_BRANCH_NOT_CANONICAL",
                    f"Source checkout is on '{install.branch}', not {' or '.join(CANONICAL_SOURCE_BRANCHES)}.",
                    "Switch to `development` (or `master`) before upgrading, or upgrade manually on your branch.",
                )
            return {"checks": ["clean-tree", "canonical-branch"]}
        if install.method in ("pip", "pipx"):
            if not release.wheel():
                raise UpgradeError(
                    "preflight",
                    "ASSET_MISSING",
                    f"Release {release.tag} has no wheel for {PACKAGE_NAME}.",
                    "Check the release.yml build-python job uploaded dist/*.whl.",
                )
            if install.method == "pipx" and not shutil.which("pipx"):
                raise UpgradeError("preflight", "PIPX_MISSING", "pipx install detected but `pipx` is not on PATH.")
            return {"checks": ["wheel-asset"]}
        tag = platform_tag()
        if not release.binary(tag):
            raise UpgradeError(
                "preflight",
                "ASSET_MISSING",
                f"Release {release.tag} has no standalone binary for platform '{tag}'.",
                "Install via pip/pipx instead, or add this platform to the release.yml binary matrix.",
            )
        if not os.access(Path(install.binary_path).parent, os.W_OK):
            raise UpgradeError(
                "preflight",
                "BINARY_NOT_WRITABLE",
                f"Cannot write to {Path(install.binary_path).parent}.",
                "Re-run with permission to replace the binary, or reinstall to a user-writable location.",
            )
        return {"checks": ["binary-asset", "binary-writable"]}

    def snapshot(self, install: InstallInfo) -> Dict[str, Any]:
        snap: Dict[str, Any] = {"method": install.method, "version": install.version, "taken_at": _utc_now()}
        if install.method == "source":
            snap.update({"repo_root": install.repo_root, "branch": install.branch, "head_sha": install.head_sha})
        elif install.method == "binary":
            self.backup_dir.mkdir(parents=True, exist_ok=True)
            backup = self.backup_dir / f"hath0r-{install.version}-{int(time.time())}"
            shutil.copy2(install.binary_path, backup)
            snap.update({"binary_path": install.binary_path, "backup_path": str(backup)})
        return snap

    # ── install ──
    def _pip_install(self, install: InstallInfo, target: str) -> Tuple[int, str, str]:
        if install.method == "pipx":
            return self.runner(["pipx", "install", "--force", target], timeout=900)
        return self.runner(
            [install.python, "-m", "pip", "install", "--upgrade", "--force-reinstall", target], timeout=900
        )

    def install(
        self, install: InstallInfo, release: ReleaseInfo, staging: Path, verifier: "UpgradeVerifierBot"
    ) -> Dict[str, Any]:
        if install.method == "source":
            return self._install_source(install, release)
        if install.method in ("pip", "pipx"):
            wheel = release.wheel()
            assert wheel is not None
            artifact = self.download_verified(release, wheel, staging)
            code, out, err = self._pip_install(install, artifact["path"])
            if code != 0:
                raise UpgradeError(
                    "install", "PIP_INSTALL_FAILED", f"{install.method} install failed: {err or out}"[:2000]
                )
            return {"artifact": artifact, "installer": install.method}
        return self._install_binary(install, release, staging, verifier)

    def _install_source(self, install: InstallInfo, release: ReleaseInfo) -> Dict[str, Any]:
        root = Path(install.repo_root)
        code, _, err = self.runner(["git", "fetch", "--tags", "origin", install.branch], cwd=root, timeout=300)
        if code != 0:
            raise UpgradeError("install", "GIT_FETCH_FAILED", f"git fetch failed: {err}", "Check network / git auth.")
        code, _, err = self.runner(["git", "merge", "--ff-only", f"origin/{install.branch}"], cwd=root, timeout=120)
        if code != 0:
            raise UpgradeError(
                "install",
                "GIT_FAST_FORWARD_FAILED",
                f"Cannot fast-forward {install.branch} to origin/{install.branch}: {err}",
                "Your local branch has diverged. Reconcile it with origin manually (rebase or reset).",
            )
        _, new_sha, _ = self.runner(["git", "rev-parse", "HEAD"], cwd=root, timeout=30)
        code, out, err = self.runner([install.python, "-m", "pip", "install", "-e", str(root)], cwd=root, timeout=900)
        if code != 0:
            raise UpgradeError("install", "PIP_INSTALL_FAILED", f"Editable reinstall failed: {err or out}"[:2000])
        source_version = (root / "VERSION").read_text(encoding="utf-8").strip() if (root / "VERSION").is_file() else ""
        if source_version and compare_versions(source_version, release.version) < 0:
            raise UpgradeError(
                "install",
                "SOURCE_BEHIND_RELEASE",
                f"origin/{install.branch} is at {source_version}, older than release {release.version}.",
                "Switch the checkout to `master` (release line) or wait for the release to merge back to development.",
            )
        return {"from_sha": install.head_sha, "to_sha": new_sha.strip(), "source_version": source_version}

    def _install_binary(
        self, install: InstallInfo, release: ReleaseInfo, staging: Path, verifier: "UpgradeVerifierBot"
    ) -> Dict[str, Any]:
        asset = release.binary(platform_tag())
        assert asset is not None
        artifact = self.download_verified(release, asset, staging)
        staged = Path(artifact["path"])
        staged.chmod(0o755)
        # Test the new binary *before* it replaces the working one.
        pre = verifier.verify(release.version, level="smoke", command=[str(staged)])
        if not pre["passed"]:
            raise UpgradeError(
                "verify",
                "STAGED_BINARY_FAILED",
                f"Staged binary failed pre-swap checks: {pre['summary']}",
                "The live binary was not touched. Report the failing checks on the release.",
            )
        target = Path(install.binary_path)
        tmp = target.with_name(target.name + ".new")
        shutil.copy2(staged, tmp)
        os.replace(tmp, target)
        return {"artifact": artifact, "replaced": str(target), "pre_swap_verification": pre["summary"]}

    # ── rollback ──
    def rollback(self, snapshot: Dict[str, Any], install: Optional[InstallInfo] = None) -> Dict[str, Any]:
        """Restore the install recorded in ``snapshot``."""
        method = snapshot.get("method")
        try:
            if method == "source":
                root = Path(snapshot["repo_root"])
                code, _, err = self.runner(["git", "reset", "--hard", snapshot["head_sha"]], cwd=root, timeout=120)
                if code != 0:
                    return {"success": False, "error": f"git reset failed: {err}"}
                code, out, err = self.runner(
                    [self.python, "-m", "pip", "install", "-e", str(root)], cwd=root, timeout=900
                )
                ok = code == 0
                return {"success": ok, "restored_sha": snapshot["head_sha"], "error": None if ok else err or out}
            if method == "binary":
                shutil.copy2(snapshot["backup_path"], snapshot["binary_path"])
                return {"success": True, "restored": snapshot["binary_path"]}
            if method in ("pip", "pipx"):
                prev = snapshot.get("version", "")
                release = self.fetch_release(prev)
                wheel = release.wheel()
                if not wheel:
                    return {"success": False, "error": f"No wheel published for previous version {prev}."}
                with tempfile.TemporaryDirectory(prefix="hath0r-rollback-") as tmp:
                    artifact = self.download_verified(release, wheel, Path(tmp))
                    info = install or InstallInfo(method=method, version=prev, python=self.python)
                    code, out, err = self._pip_install(info, artifact["path"])
                ok = code == 0
                return {"success": ok, "restored_version": prev, "error": None if ok else err or out}
            return {"success": False, "error": f"Unknown install method '{method}'."}
        except UpgradeError as exc:
            return {"success": False, "error": exc.message}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    # ── orchestration ──
    def run(
        self,
        version: Optional[str] = None,
        *,
        force: bool = False,
        dry_run: bool = False,
        test_level: str = "smoke",
        auto_rollback: bool = True,
        verifier: Optional["UpgradeVerifierBot"] = None,
    ) -> Dict[str, Any]:
        """Full pipeline: detect → check → preflight → snapshot → install → verify → (rollback)."""
        started = time.perf_counter()
        report: Dict[str, Any] = {
            "schema": REPORT_SCHEMA,
            "run_id": f"upg_{int(time.time())}_{os.getpid()}",
            "started_at": _utc_now(),
            "dry_run": dry_run,
            "test_level": test_level,
            "stages": [],
            "outcome": "failed",
            "success": False,
        }

        def stage(name: str, status: str, **data: Any) -> None:
            report["stages"].append({"stage": name, "status": status, **data})

        verifier = verifier or UpgradeVerifierBot(cwd=self.cwd, runner=self.runner, python=self.python)
        install: Optional[InstallInfo] = None
        snapshot: Optional[Dict[str, Any]] = None
        locked = False
        staging = Path(tempfile.mkdtemp(prefix="hath0r-upgrade-"))
        try:
            install = self.detect_install()
            report["install"] = install.to_dict()
            report["from_version"] = install.version
            stage("detect", "ok", method=install.method)

            release = self.fetch_release(version)
            report["release"] = release.to_dict()
            report["to_version"] = release.version
            cmp = compare_versions(release.version, install.version)
            stage("check", "ok", latest=release.version, current=install.version)
            if cmp <= 0 and not force:
                report.update(
                    outcome="up-to-date",
                    success=True,
                    message=f"hath0r {install.version} is already up to date (latest {release.version}).",
                )
                return report
            if cmp < 0 and not version:
                raise UpgradeError("check", "DOWNGRADE_REFUSED", "Installed version is newer than the latest release.")

            if not dry_run:
                self._acquire_lock()
                locked = True
            pre = self.preflight(install, release)
            stage("preflight", "ok", **pre)

            if dry_run:
                report.update(
                    outcome="dry-run",
                    success=True,
                    message=(
                        f"[DRY-RUN] Would upgrade hath0r {install.version} → {release.version} via {install.method}, "
                        f"then run {test_level} verification with auto-rollback={'on' if auto_rollback else 'off'}."
                    ),
                )
                return report

            report["baseline"] = verifier.baseline(command=verifier.command_for(install))
            stage("baseline", "ok", doctor_failed=report["baseline"].get("doctor_failed"))

            snapshot = self.snapshot(install)
            report["snapshot"] = snapshot
            stage("snapshot", "ok")

            installed = self.install(install, release, staging, verifier)
            stage("install", "ok", **{k: v for k, v in installed.items() if k != "pre_swap_verification"})

            result = verifier.verify(
                release.version,
                level=test_level,
                command=verifier.command_for(install),
                baseline=report["baseline"],
                repo_root=install.repo_root or None,
            )
            report["verification"] = result
            if not result["passed"]:
                raise UpgradeError(
                    "verify",
                    "VERIFICATION_FAILED",
                    f"Post-install verification failed: {result['summary']}",
                    "See the failing checks in the report; the previous version has been restored if rollback is on.",
                )
            stage("verify", "ok", summary=result["summary"])
            report.update(
                outcome="upgraded",
                success=True,
                message=f"Upgraded hath0r {install.version} → {release.version} ({install.method}); all checks passed.",
            )
            return report
        except UpgradeError as exc:
            report["failure"] = exc.to_dict()
            stage(exc.stage, "failed", code=exc.code)
            report["message"] = f"Upgrade failed at {exc.stage}: {exc.message}"
            if snapshot and auto_rollback and exc.stage in ("install", "verify"):
                rb = self.rollback(snapshot, install)
                if rb.get("success") and install is not None:
                    rb["verification"] = verifier.verify(
                        snapshot["version"], level="smoke", command=verifier.command_for(install)
                    )
                    rb["success"] = bool(rb["verification"]["passed"])
                report["rollback"] = rb
                stage("rollback", "ok" if rb.get("success") else "failed")
                report["outcome"] = "rolled-back" if rb.get("success") else "rollback-failed"
            return report
        except Exception as exc:  # pragma: no cover - last-resort guard
            report["failure"] = {"stage": "internal", "code": "INTERNAL_ERROR", "message": str(exc), "hint": ""}
            report["message"] = f"Upgrade bot internal error: {exc}"
            if snapshot and auto_rollback:
                report["rollback"] = self.rollback(snapshot, install)
                report["outcome"] = "rolled-back" if report["rollback"].get("success") else "rollback-failed"
            return report
        finally:
            shutil.rmtree(staging, ignore_errors=True)
            if locked:
                self._release_lock()
            report["finished_at"] = _utc_now()
            report["duration_ms"] = int((time.perf_counter() - started) * 1000)
            report["exit_code"] = exit_code_for(report)
            if not dry_run:
                self.save_report(report)

    # ── persistence ──
    def save_report(self, report: Dict[str, Any]) -> None:
        try:
            self.state_dir.mkdir(parents=True, exist_ok=True)
            self.report_file.write_text(json.dumps(report, indent=2), encoding="utf-8")
            summary = {k: report.get(k) for k in ("run_id", "finished_at", "outcome", "from_version", "to_version")}
            if report.get("failure"):
                summary["failure"] = report["failure"].get("code")
            with self.history_file.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(summary) + "\n")
        except OSError:
            pass  # reporting must never break the upgrade

    def status(self, limit: int = 10) -> Dict[str, Any]:
        last = None
        if self.report_file.is_file():
            try:
                last = json.loads(self.report_file.read_text(encoding="utf-8"))
            except ValueError:
                last = None
        history: List[Dict[str, Any]] = []
        if self.history_file.is_file():
            for line in self.history_file.read_text(encoding="utf-8").splitlines()[-limit:]:
                try:
                    history.append(json.loads(line))
                except ValueError:
                    continue
        return {
            "success": True,
            "state_dir": str(self.state_dir),
            "last_run": last,
            "history": history,
            "message": f"Last upgrade run: {last['outcome']} at {last.get('finished_at')}."
            if last
            else "No upgrade runs recorded yet.",
        }

    def last_snapshot(self) -> Optional[Dict[str, Any]]:
        status = self.status(limit=1)
        last = status.get("last_run") or {}
        snap = last.get("snapshot")
        return snap if isinstance(snap, dict) else None

    # ── scheduling ──
    def schedule_spec(self, hour: int = 4, minute: int = 17, file_issue: bool = True) -> Dict[str, Any]:
        """Render a launchd plist (macOS) and a crontab line for an unattended nightly run."""
        exe = shutil.which("hath0r") or f"{self.python} -m hath0r_cli"
        args = exe.split() + ["--quiet", "-o", "json", "upgrade", "run"] + (["--file-issue"] if file_issue else [])
        log = self.state_dir / "scheduled.log"
        prog_args = "\n".join(f"    <string>{a}</string>" for a in args)
        plist = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>{LAUNCHD_LABEL}</string>
  <key>ProgramArguments</key>
  <array>
{prog_args}
  </array>
  <key>StartCalendarInterval</key>
  <dict>
    <key>Hour</key>
    <integer>{hour}</integer>
    <key>Minute</key>
    <integer>{minute}</integer>
  </dict>
  <key>StandardOutPath</key>
  <string>{log}</string>
  <key>StandardErrorPath</key>
  <string>{log}</string>
</dict>
</plist>
"""
        cron = f"{minute} {hour} * * * {' '.join(args)} >> {log} 2>&1"
        plist_path = Path.home() / "Library" / "LaunchAgents" / f"{LAUNCHD_LABEL}.plist"
        return {"success": True, "plist": plist, "plist_path": str(plist_path), "cron": cron, "args": args}


def exit_code_for(report: Dict[str, Any]) -> int:
    if report.get("success"):
        return EXIT_OK
    if report.get("outcome") == "rollback-failed":
        return EXIT_ROLLBACK_FAILED
    return EXIT_FAILED


# ── UpgradeVerifierBot ─────────────────────────────────────────────────────────

_IMPORT_SCAN = r"""
import importlib, json, sys
from hath0r_cli import __version__
from hath0r_cli.lazy_group import COMMAND_REGISTRY
failed = {}
for name, (mod, attr) in COMMAND_REGISTRY.items():
    try:
        getattr(importlib.import_module(mod), attr)
    except Exception as exc:
        failed[name] = f"{type(exc).__name__}: {exc}"[:300]
print(json.dumps({"version": __version__, "total": len(COMMAND_REGISTRY), "failed": failed}))
"""


@dataclass
class UpgradeVerifierBot:
    """Runs the post-install test suite against the installed CLI in fresh subprocesses."""

    cwd: Path = field(default_factory=Path.cwd)
    runner: Runner = field(default=default_runner, repr=False)
    python: str = field(default_factory=lambda: sys.executable)

    def command_for(self, install: InstallInfo) -> List[str]:
        if install.method == "binary":
            return [install.binary_path]
        return [install.python, "-m", PACKAGE_NAME]

    def _cli_json(self, command: List[str], args: List[str], timeout: int = 180) -> Tuple[int, Any, str]:
        code, out, err = self.runner([*command, "--quiet", "-o", "json", *args], cwd=self.cwd, timeout=timeout)
        try:
            return code, json.loads(out), err
        except ValueError:
            return code, None, err or out

    def _doctor_failed(self, command: List[str]) -> Tuple[Optional[int], str]:
        _, data, err = self._cli_json(command, ["doctor"])
        if isinstance(data, dict):
            counts = (data.get("data") or {}).get("counts") or {}
            if "failed" in counts:
                return int(counts["failed"]), ""
        return None, (_last_line(err) or "doctor produced no JSON envelope")[:500]

    def baseline(self, command: Optional[List[str]] = None) -> Dict[str, Any]:
        command = command or [self.python, "-m", PACKAGE_NAME]
        failed, err = self._doctor_failed(command)
        return {"doctor_failed": failed, "doctor_error": err or None, "taken_at": _utc_now()}

    def verify(
        self,
        target_version: str,
        *,
        level: str = "smoke",
        command: Optional[List[str]] = None,
        baseline: Optional[Dict[str, Any]] = None,
        repo_root: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Run checks; returns ``{"passed": bool, "checks": [...], "summary": str}``."""
        command = command or [self.python, "-m", PACKAGE_NAME]
        checks: List[Dict[str, Any]] = []

        def add(name: str, passed: bool, detail: str = "", required: bool = True) -> None:
            checks.append({"name": name, "passed": passed, "required": required, "detail": detail[:1500]})

        # 1. Version reports the target release.
        code, data, err = self._cli_json(command, ["--version"], timeout=60)
        reported = ((data or {}).get("data") or {}).get("version") if isinstance(data, dict) else None
        if reported and normalize_version(target_version):
            ok = compare_versions(str(reported), target_version) >= 0
            add("version", ok, f"reported {reported}, expected ≥ {target_version}")
        else:
            add("version", False, f"exit {code}: {err}")

        # 2. Every registered command imports (lazy group silently hides broken commands).
        if command[-1] == PACKAGE_NAME:
            code, out, err = self.runner([command[0], "-c", _IMPORT_SCAN], cwd=self.cwd, timeout=240)
            try:
                scan = json.loads(out.splitlines()[-1])
                failed = scan.get("failed") or {}
                add(
                    "command-imports",
                    not failed,
                    f"{scan['total'] - len(failed)}/{scan['total']} commands import"
                    + (f"; broken: {json.dumps(failed)}" if failed else ""),
                )
            except (ValueError, IndexError, KeyError):
                add("command-imports", False, f"exit {code}: {err or out}")
        else:
            code, out, err = self.runner([*command, "--help"], cwd=self.cwd, timeout=60)
            add("cli-help", code == 0, err or "root --help ok")

        # 3. doctor envelope + no regression versus the pre-upgrade baseline.
        failed_now, derr = self._doctor_failed(command)
        if failed_now is None:
            add("doctor", False, derr)
        else:
            before = (baseline or {}).get("doctor_failed")
            ok = before is None or failed_now <= int(before)
            add("doctor", ok, f"failed checks: {failed_now} (baseline {before})")

        # 4. Factory manifests still validate (configuration compatibility).
        code, data, err = self._cli_json(command, ["factory", "validate"], timeout=180)
        state = data.get("state") if isinstance(data, dict) else None
        add(
            "factory-validate",
            code == 0 and state in ("ok", "degraded"),
            f"state={state} {_last_line(err)}".strip(),
            required=False,
        )

        # 5. Full unit-test suite (source checkouts only).
        if level == "full":
            if repo_root and (Path(repo_root) / "tests").is_dir():
                code, out, err = self.runner(
                    [command[0], "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider", "tests/unit"],
                    cwd=Path(repo_root),
                    timeout=1800,
                )
                tail = "\n".join((out or err).splitlines()[-15:])
                add("unit-tests", code == 0, tail)
            else:
                add("unit-tests", True, "skipped: full suite only runs for source checkouts", required=False)

        required_failures = [c for c in checks if c["required"] and not c["passed"]]
        passed_count = sum(1 for c in checks if c["passed"])
        summary = f"{passed_count}/{len(checks)} checks passed"
        if required_failures:
            summary += "; failing: " + ", ".join(c["name"] for c in required_failures)
        return {"passed": not required_failures, "level": level, "checks": checks, "summary": summary}


# ── UpgradeAnnouncerBot ────────────────────────────────────────────────────────


@dataclass
class UpgradeAnnouncerBot:
    """Announces upgrade outcomes; files a de-duplicated GitHub issue for failures (opt-in)."""

    cwd: Path = field(default_factory=Path.cwd)
    repo: str = DEFAULT_REPO
    runner: Runner = field(default=default_runner, repr=False)

    def issue_title(self, report: Dict[str, Any]) -> str:
        failure = report.get("failure") or {}
        return (
            f"[upgrade-bot] hath0r {report.get('to_version', '?')} upgrade failed: "
            f"{failure.get('code', 'UNKNOWN')} at {failure.get('stage', '?')}"
        )

    def issue_body(self, report: Dict[str, Any]) -> str:
        failure = report.get("failure") or {}
        install = report.get("install") or {}
        rollback = report.get("rollback") or {}
        lines = [
            "## Automated upgrade failure",
            "",
            f"- **Upgrade:** `{report.get('from_version', '?')}` → `{report.get('to_version', '?')}`",
            f"- **Install method:** `{install.get('method', '?')}` · Python `{platform.python_version()}` · "
            f"`{platform.system()} {platform.machine()}`",
            f"- **Failed stage:** `{failure.get('stage')}` · code `{failure.get('code')}`",
            f"- **Outcome:** `{report.get('outcome')}`"
            + (" — previous version restored and re-verified." if report.get("outcome") == "rolled-back" else ""),
            f"- **Run:** `{report.get('run_id')}` at {report.get('finished_at') or report.get('started_at')}",
            "",
            "### Error",
            "```",
            str(failure.get("message", ""))[:3000],
            "```",
        ]
        if failure.get("hint"):
            lines += ["", f"**Suggested fix:** {failure['hint']}"]
        checks = (report.get("verification") or {}).get("checks") or []
        if checks:
            lines += ["", "### Verification checks", "", "| Check | Result | Detail |", "|---|---|---|"]
            for c in checks:
                detail = str(c.get("detail", "")).replace("|", "\\|").replace("\n", " ")[:300]
                lines.append(f"| {c['name']} | {'✅' if c['passed'] else '❌'} | {detail} |")
        if rollback:
            lines += ["", f"### Rollback\n\n`{json.dumps({k: v for k, v in rollback.items() if k != 'verification'})}`"]
        lines += [
            "",
            "### Reproduce",
            "```sh",
            f"hath0r upgrade run --version {report.get('to_version', '<ver>')} --tests {report.get('test_level', 'smoke')}",
            "hath0r upgrade status",
            "```",
            "",
            "_Filed automatically by `upgrade-bot` (docs/governance/runbooks/upgrade-runbook.md)._",
        ]
        return "\n".join(lines)

    def _find_open_issue(self, title: str) -> Optional[Dict[str, Any]]:
        code, out, _ = self.runner(
            [
                "gh",
                "issue",
                "list",
                "--repo",
                self.repo,
                "--state",
                "open",
                "--search",
                f'"{title}" in:title',
                "--json",
                "number,title,url",
                "--limit",
                "20",
            ],
            timeout=60,
        )
        if code != 0:
            return None
        try:
            return next((i for i in json.loads(out or "[]") if i.get("title") == title), None)
        except ValueError:
            return None

    def file_issue(self, report: Dict[str, Any], dry_run: bool = False) -> Dict[str, Any]:
        title, body = self.issue_title(report), self.issue_body(report)
        if dry_run:
            return {"success": True, "dry_run": True, "title": title, "action": f"[DRY-RUN] gh issue create '{title}'"}
        existing = self._find_open_issue(title)
        if existing:
            code, _, err = self.runner(
                [
                    "gh",
                    "issue",
                    "comment",
                    str(existing["number"]),
                    "--repo",
                    self.repo,
                    "--body",
                    f"Failure reproduced again by upgrade-bot run `{report.get('run_id')}`.\n\n" + body,
                ],
                timeout=60,
            )
            return {
                "success": code == 0,
                "deduplicated": True,
                "number": existing["number"],
                "url": existing.get("url"),
                "error": err if code else None,
            }
        base = ["gh", "issue", "create", "--repo", self.repo, "--title", title, "--body", body]
        code, out, err = self.runner(base + ["--label", "bug,upgrade-bot"], timeout=60)
        if code != 0:  # labels may not exist in the repo — retry without them
            code, out, err = self.runner(base, timeout=60)
        m = re.search(r"/issues/(\d+)", out or "")
        return {
            "success": code == 0,
            "url": out.strip() if code == 0 else None,
            "number": int(m.group(1)) if m else None,
            "error": err if code else None,
        }

    def announce(
        self,
        report: Dict[str, Any],
        *,
        file_issue: bool = False,
        speak: bool = True,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Broadcast the outcome. Failures produce an actionable message (and optionally an issue)."""
        outcome = report.get("outcome", "failed")
        failed = not report.get("success")
        message = report.get("message") or f"Upgrade outcome: {outcome}."
        failure = report.get("failure") or {}
        if failed and failure.get("hint"):
            message = f"{message} Fix: {failure['hint']}"
        if outcome == "rollback-failed":
            message = "CRITICAL: rollback failed — the hath0r install needs manual repair. " + message
        result: Dict[str, Any] = {
            "success": not failed,
            "outcome": outcome,
            "severity": "critical" if outcome == "rollback-failed" else ("error" if failed else "info"),
            "message": message,
            "channels": ["console", "report"],
        }
        if speak and not dry_run:
            try:
                from hath0r_cli.bots.voice_speaker import SpokenNotificationServiceBot

                spoken = (
                    f"hath0r upgrade to {report.get('to_version')} failed at {failure.get('stage')}. "
                    f"{'Previous version restored.' if outcome == 'rolled-back' else 'Operator attention needed.'}"
                    if failed
                    else message
                )
                SpokenNotificationServiceBot(cwd=self.cwd).queue_message(
                    spoken, priority="high" if failed else "normal", category="upgrade"
                )
                result["channels"].append("voice-queue")
            except Exception:
                pass  # voice is best-effort
        if failed and file_issue:
            result["issue"] = self.file_issue(report, dry_run=dry_run)
            if result["issue"].get("success"):
                result["channels"].append("github-issue")
        return result
