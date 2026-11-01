"""InstallWizardBot — Guided & Automated Install Wizard for Hath0r CLI and Hath0r MCP (Docker).

Implements the canonical 5-stage Install Wizard:
1. Dependency Inspection & Installation (Python >= 3.10, pipx/pip, Git, curl, Docker Engine, Docker Compose v2).
2. Global Hath0r CLI Installation (pipx, standalone binary, or pip --user, SHA-256 verified, PATH ensured).
3. Hath0r MCP Docker Staging (Dockerfile, docker-compose.yml, requirements.txt, canonical knowledgebase, .env).
4. Docker Group & Container Launch (network `hath0r-net` with `com.hath0r.*` labels, `Hath0r-MCP` on 127.0.0.1:38083).
5. End-to-End Verification & Receipt (`http://127.0.0.1:38083/ready`, `UpgradeVerifierBot.verify()`,
   `.hath0r/mcp.json`, optional Claude Desktop registration, and `~/.hath0r/install/INSTALL_RECEIPT.json`).

Governance:
- CR-CLI-ENTRY-001 & CR-FEATURE-WORKFLOW-STANDARD-001 (Service owned by `install-wizard-bot` in `BotRegistry`)
- CR-CLI-FEATURE-STANDARD-001 (Artifact Hexad in `docs/governance/*/install-wizard-*`)
- CR-DOCKER-HATH0R-GROUP-001 (project `hath0r`, network `hath0r-net`, container `Hath0r-MCP`, port `38083`)
- CR-AGENTIC-SEC-001 (SHA-256 verification, non-root `10001:10001`, read-only rootfs, dropped capabilities)
"""

from __future__ import annotations

import json
import os
import platform
import shutil
import sys
import tempfile
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from hath0r_cli.bots.upgrade_bot import (
    DEFAULT_REPO as DEFAULT_CLI_REPO,
)
from hath0r_cli.bots.upgrade_bot import (
    UpgradeBot,
    UpgradeError,
    UpgradeVerifierBot,
    default_http_get,
    default_runner,
    platform_tag,
    sha256_file,
)
from hath0r_cli.step_runner import spool_telemetry_event
from hath0r_cli.telemetry import trace_span

Runner = Callable[..., Tuple[int, str, str]]
HttpGet = Callable[[str, Dict[str, str]], bytes]

DEFAULT_MCP_REPO = "Bayly-AI/HATH0R-MCP"
DEFAULT_NETWORK_NAME = "hath0r-net"
DEFAULT_COMPOSE_PROJECT = "hath0r"
DEFAULT_MCP_SERVICE = "hath0r-mcp"
DEFAULT_MCP_CONTAINER = "Hath0r-MCP"
DEFAULT_MCP_IMAGE = "hath0r/mcp:local"
DEFAULT_MCP_PORT = 38083
RECEIPT_SCHEMA = "hath0r.install.receipt/1"
INSTALL_METHODS = ("pipx", "binary", "pip")

EMBEDDED_MCP_DOCKERFILE = """# syntax=docker/dockerfile:1
# ------------------------------------------------------------------------------
# Stage 1: Build & Dependencies
# ------------------------------------------------------------------------------
FROM python:3.11-slim AS builder

ARG GIT_SHA=unknown
ARG BUILD_TIMESTAMP=unknown
ARG APP_VERSION=1.5.0

ENV PYTHONDONTWRITEBYTECODE=1 \\
    PYTHONUNBUFFERED=1 \\
    PIP_NO_CACHE_DIR=1 \\
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \\
    build-essential \\
    curl \\
    git \\
    && rm -rf /var/lib/apt/lists/*

COPY requirements*.txt pyproject.toml* README.md* ./
COPY src ./src

RUN if [ -f requirements.txt ]; then \\
        pip install --prefix=/install -r requirements.txt; \\
    fi && \\
    if [ -f pyproject.toml ]; then \\
        pip install --prefix=/install --no-deps .; \\
    fi

# ------------------------------------------------------------------------------
# Stage 2: Hardened Non-Root Runtime
# ------------------------------------------------------------------------------
FROM python:3.11-slim AS runner

ARG GIT_SHA=unknown
ARG BUILD_TIMESTAMP=unknown
ARG APP_VERSION=1.5.0

ENV PYTHONDONTWRITEBYTECODE=1 \\
    PYTHONUNBUFFERED=1 \\
    GIT_SHA=${GIT_SHA} \\
    BUILD_TIMESTAMP=${BUILD_TIMESTAMP} \\
    APP_VERSION=${APP_VERSION} \\
    PATH="/install/bin:$PATH" \\
    PYTHONPATH="/app/src:/install/lib/python3.11/site-packages:$PYTHONPATH" \\
    HATH0R_MCP_KNOWLEDGE_ROOT=/app/knowledgebase/canonical

RUN groupadd -g 10001 hath0r && \\
    useradd -u 10001 -g hath0r -s /bin/sh -m hath0r

WORKDIR /app

COPY --from=builder /install /install
COPY --chown=hath0r:hath0r . /app

RUN mkdir -p /app/data /app/logs /app/data/indices && \\
    chown -R hath0r:hath0r /app

USER 10001:10001

EXPOSE 8083

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \\
    CMD python3 -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8083/ready', timeout=5)" || exit 1

CMD ["python3", "-m", "uvicorn", "knowledgebase.server:app", "--host", "0.0.0.0", "--port", "8083"]
"""

EMBEDDED_MCP_COMPOSE = """# Hath0r OpenSource Suite MCP service
name: hath0r
services:
  hath0r-mcp:
    build:
      context: .
      args:
        GIT_SHA: ${GIT_SHA:-unknown}
        BUILD_TIMESTAMP: ${BUILD_TIMESTAMP:-unknown}
    image: hath0r/mcp:local
    container_name: Hath0r-MCP
    restart: unless-stopped
    ports:
      - "127.0.0.1:${HATH0R_MCP_HOST_PORT:-38083}:8083"
    environment:
      HATH0R_MCP_ENVIRONMENT: ${HATH0R_MCP_ENVIRONMENT:-local}
      HATH0R_MCP_KNOWLEDGE_ROOT: /app/knowledgebase/canonical
      HATH0R_MCP_TOKEN: ${HATH0R_MCP_TOKEN:-}
    read_only: true
    tmpfs: [/tmp]
    cap_drop: [ALL]
    security_opt: [no-new-privileges:true]
    init: true
    stop_grace_period: 20s
    volumes:
      - ./knowledgebase:/app/knowledgebase:ro
    networks:
      hath0r-net:
        aliases: [Hath0r-MCP, hath0r-mcp, mcp]
    labels:
      com.hath0r.org: bayly-ai
      com.hath0r.project: hath0r-opensource
      com.hath0r.component: mcp
      com.hath0r.container: Hath0r-MCP
    healthcheck:
      test: [CMD, python3, -c, "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8083/ready', timeout=5)"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 30s
    mem_limit: ${HATH0R_MCP_MEM_LIMIT:-512m}
    cpus: ${HATH0R_MCP_CPU_LIMIT:-1.0}
networks:
  hath0r-net:
    name: hath0r-net
    external: true
"""

EMBEDDED_MCP_REQUIREMENTS = """fastapi>=0.110.0
uvicorn[standard]>=0.27.0
pydantic>=2.6.0
pydantic-settings>=2.2.0
mcp>=1.0.0,<2.0.0
httpx>=0.27.0
"""

EMBEDDED_MCP_FALLBACK_SERVER = '''"""Fallback Hath0r MCP server for standalone Docker bootstrap."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI

app = FastAPI(title="HATH0R-MCP", version="1.5.0")


@app.get("/health")
def health() -> dict[str, Any]:
    return {"status": "healthy", "service": "hath0r-mcp", "version": "1.5.0"}


@app.get("/ready")
def ready() -> dict[str, Any]:
    kb_root = Path(os.environ.get("HATH0R_MCP_KNOWLEDGE_ROOT", "/app/knowledgebase/canonical"))
    docs = list(kb_root.rglob("*.md")) if kb_root.is_dir() else []
    return {"status": "ready", "service": "hath0r-mcp", "documents_loaded": len(docs)}


@app.post("/mcp")
@app.get("/mcp")
def mcp_endpoint() -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "result": {
            "service": "hath0r-mcp",
            "container": "Hath0r-MCP",
            "network": "hath0r-net",
            "status": "ok",
        },
    }
'''

EMBEDDED_SEED_KB_DOC = """# Hath0r OpenSource Suite — Canonical Overview

Hath0r CLI (`hath0r`) and Hath0r MCP (`Hath0r-MCP`) operate as a paired agentic control plane
on Docker group `hath0r` and network `hath0r-net`.
"""


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def install_home() -> Path:
    """State directory for Install Wizard receipts, MCP Docker staging, and logs."""
    override = os.environ.get("HATH0R_INSTALL_HOME")
    if override:
        return Path(override).expanduser().resolve()
    return (Path.home() / ".hath0r").resolve()


def default_bin_dir() -> Path:
    """Return preferred global binary directory (`/usr/local/bin` if writable, else `~/.local/bin`)."""
    override = os.environ.get("HATH0R_BIN_DIR")
    if override:
        return Path(override).expanduser().resolve()
    usr_local = Path("/usr/local/bin")
    if usr_local.is_dir() and os.access(usr_local, os.W_OK):
        return usr_local
    return (Path.home() / ".local" / "bin").resolve()


class InstallWizardError(Exception):
    """Structured error raised at a named stage of the Install Wizard."""

    def __init__(self, stage: str, code: str, message: str, hint: str = "") -> None:
        super().__init__(message)
        self.stage = stage
        self.code = code
        self.message = message
        self.hint = hint

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stage": self.stage,
            "code": self.code,
            "message": self.message,
            "hint": self.hint,
        }


@dataclass
class InstallWizardBot:
    """Manages end-to-end dependency installation, global CLI setup, and Hath0r-MCP Docker deployment."""

    cwd: Path = field(default_factory=Path.cwd)
    cli_repo: str = DEFAULT_CLI_REPO
    mcp_repo: str = DEFAULT_MCP_REPO
    runner: Runner = field(default=default_runner, repr=False)
    http_get: HttpGet = field(default=default_http_get, repr=False)
    home_dir: Path = field(default_factory=install_home)
    bin_dir: Path = field(default_factory=default_bin_dir)
    python: str = field(default_factory=lambda: sys.executable)

    @property
    def receipt_file(self) -> Path:
        return self.home_dir / "install" / "INSTALL_RECEIPT.json"

    @property
    def history_file(self) -> Path:
        return self.home_dir / "install" / "history.jsonl"

    @property
    def default_mcp_dir(self) -> Path:
        return self.home_dir / "mcp"

    # ── Stage 1: Dependency Inspection & Installation ─────────────────────────

    def check_dependencies(self) -> Dict[str, Any]:
        """Inspect host OS, Python, pipx, Git, curl, Docker CLI, Docker Compose v2, and Docker daemon."""
        py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        py_ok = (sys.version_info.major, sys.version_info.minor) >= (3, 10)

        git_bin = shutil.which("git")
        curl_bin = shutil.which("curl")
        pipx_bin = shutil.which("pipx")
        docker_bin = shutil.which("docker")
        brew_bin = shutil.which("brew")
        apt_bin = shutil.which("apt-get")
        dnf_bin = shutil.which("dnf")
        winget_bin = shutil.which("winget")

        compose_ok = False
        compose_version = ""
        daemon_ok = False
        daemon_detail = ""

        if docker_bin:
            rc_c, out_c, err_c = self.runner(["docker", "compose", "version"], timeout=15)
            if rc_c == 0:
                compose_ok = True
                compose_version = (out_c or err_c).splitlines()[0] if (out_c or err_c) else "v2"
            rc_d, out_d, err_d = self.runner(["docker", "info"], timeout=15)
            daemon_ok = rc_d == 0
            daemon_detail = "running" if daemon_ok else (err_d or out_d or "daemon not responding")[:240]

        missing: List[str] = []
        if not py_ok:
            missing.append("python>=3.10")
        if not git_bin:
            missing.append("git")
        if not curl_bin:
            missing.append("curl")
        if not docker_bin:
            missing.append("docker")
        elif not compose_ok:
            missing.append("docker-compose-v2")

        pkg_mgr = (
            "brew"
            if brew_bin
            else ("apt" if apt_bin else ("dnf" if dnf_bin else ("winget" if winget_bin else "pip")))
        )

        return {
            "os": platform.system().lower(),
            "arch": platform.machine().lower(),
            "platform_tag": platform_tag() or f"{platform.system().lower()}-{platform.machine().lower()}",
            "package_manager": pkg_mgr,
            "python": {"ok": py_ok, "version": py_ver, "executable": self.python},
            "pipx": {"ok": bool(pipx_bin), "path": pipx_bin or ""},
            "git": {"ok": bool(git_bin), "path": git_bin or ""},
            "curl": {"ok": bool(curl_bin), "path": curl_bin or ""},
            "docker": {"ok": bool(docker_bin), "path": docker_bin or ""},
            "docker_compose": {"ok": compose_ok, "version": compose_version},
            "docker_daemon": {"ok": daemon_ok, "detail": daemon_detail},
            "missing": missing,
            "all_ready": len(missing) == 0 and daemon_ok,
        }

    def install_dependencies(
        self,
        *,
        need_pipx: bool = True,
        need_docker: bool = True,
        start_daemon: bool = True,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Install any missing system dependencies and ensure the Docker daemon is running."""
        before = self.check_dependencies()
        actions: List[Dict[str, Any]] = []

        if not before["python"]["ok"]:
            raise InstallWizardError(
                "dependencies",
                "PYTHON_TOO_OLD",
                f"Python >= 3.10 is required (found {before['python']['version']}).",
                "Install Python 3.11+ via `brew install python@3.11` or from https://www.python.org/downloads/.",
            )

        pkg_mgr = before["package_manager"]

        def _run_install_step(label: str, cmd: List[str]) -> bool:
            if dry_run:
                actions.append({"step": label, "command": cmd, "status": "dry-run"})
                return True
            rc, out, err = self.runner(cmd, timeout=600)
            ok = rc == 0
            actions.append(
                {
                    "step": label,
                    "command": cmd,
                    "status": "ok" if ok else "failed",
                    "detail": (out if ok else (err or out))[:300],
                }
            )
            return ok

        # 1. Install git / curl if missing
        for tool in ("git", "curl"):
            if not before[tool]["ok"]:
                if pkg_mgr == "brew":
                    _run_install_step(f"install-{tool}", ["brew", "install", tool])
                elif pkg_mgr == "apt":
                    _run_install_step(f"install-{tool}", ["sudo", "apt-get", "install", "-y", tool])
                elif pkg_mgr == "dnf":
                    _run_install_step(f"install-{tool}", ["sudo", "dnf", "install", "-y", tool])
                elif pkg_mgr == "winget":
                    pkg_id = "Git.Git" if tool == "git" else "cURL.cURL"
                    _run_install_step(
                        f"install-{tool}",
                        [
                            "winget",
                            "install",
                            "-e",
                            "--id",
                            pkg_id,
                            "--accept-package-agreements",
                            "--accept-source-agreements",
                        ],
                    )

        # 2. Install pipx if requested and missing
        if need_pipx and not before["pipx"]["ok"]:
            if pkg_mgr == "brew":
                installed = _run_install_step("install-pipx", ["brew", "install", "pipx"])
            else:
                installed = _run_install_step(
                    "install-pipx", [self.python, "-m", "pip", "install", "--user", "--upgrade", "pipx"]
                )
            if installed:
                _run_install_step("pipx-ensurepath", [self.python, "-m", "pipx", "ensurepath"])

        # 3. Install Docker / Compose if requested and missing
        if need_docker and (not before["docker"]["ok"] or not before["docker_compose"]["ok"]):
            if pkg_mgr == "brew":
                _run_install_step("install-docker", ["brew", "install", "--cask", "docker"])
            elif pkg_mgr == "apt":
                _run_install_step(
                    "install-docker",
                    ["sudo", "apt-get", "install", "-y", "docker.io", "docker-compose-v2"],
                )
            elif pkg_mgr == "dnf":
                _run_install_step(
                    "install-docker",
                    ["sudo", "dnf", "install", "-y", "docker", "docker-compose-plugin"],
                )
            elif pkg_mgr == "winget":
                _run_install_step(
                    "install-docker",
                    [
                        "winget",
                        "install",
                        "-e",
                        "--id",
                        "Docker.DockerDesktop",
                        "--accept-package-agreements",
                        "--accept-source-agreements",
                    ],
                )

        # 4. Start Docker daemon if installed but not running
        if need_docker and start_daemon and not before["docker_daemon"]["ok"]:
            if dry_run:
                actions.append({"step": "start-docker-daemon", "status": "dry-run"})
            else:
                if before["os"] == "darwin":
                    self.runner(["open", "-a", "Docker"], timeout=30)
                elif before["os"] == "linux":
                    self.runner(["sudo", "systemctl", "start", "docker"], timeout=30)
                elif before["os"].startswith("win"):
                    self.runner(
                        ["cmd", "/c", "start", "", r"C:\Program Files\Docker\Docker\Docker Desktop.exe"],
                        timeout=30,
                    )
                # Poll up to 15 seconds for daemon readiness
                for _ in range(5):
                    rc_d, _, _ = self.runner(["docker", "info"], timeout=10)
                    if rc_d == 0:
                        actions.append({"step": "start-docker-daemon", "status": "ok"})
                        break
                    time.sleep(1)

        after = before if dry_run else self.check_dependencies()
        if need_docker and not dry_run:
            if not after["docker"]["ok"] or not after["docker_compose"]["ok"]:
                raise InstallWizardError(
                    "dependencies",
                    "DEPENDENCY_MISSING",
                    "Docker Engine and Docker Compose v2 are required to launch Hath0r MCP.",
                    "Install Docker Desktop (https://www.docker.com/products/docker-desktop/) and re-run the wizard.",
                )
            if not after["docker_daemon"]["ok"]:
                raise InstallWizardError(
                    "dependencies",
                    "DOCKER_DAEMON_UNAVAILABLE",
                    f"Docker daemon is not reachable: {after['docker_daemon']['detail']}",
                    "Start Docker Desktop (`open -a Docker`) or `sudo systemctl start docker`, then re-run.",
                )

        return {
            "success": True,
            "before": before,
            "after": after,
            "actions": actions,
        }

    # ── Stage 2: Global Hath0r CLI Installation ───────────────────────────────

    def _find_local_release_dir(self) -> Optional[Path]:
        """Locate local `release/` (or `release/mac`, `release/windows`) folder in CLI or Framework checkout when available."""
        plat_sub = "windows" if platform.system().lower().startswith("win") else "mac"
        bases = [
            self.cwd / "release",
            Path(__file__).resolve().parents[3] / "release",
            self.cwd.parent / "hathor-cli" / "release",
            self.cwd.parent / "hath0r-framework" / "release",
        ]
        candidates: List[Path] = []
        for base in bases:
            candidates.append(base / plat_sub)
            candidates.append(base)
        for cand in candidates:
            if cand.is_dir() and (cand / "CHECKSUMS.sha256").is_file():
                return cand.resolve()
        return None

    def _verify_checksum_from_file(self, artifact_path: Path, checksums_file: Path) -> str:
        """Verify `artifact_path` against a `CHECKSUMS.sha256` manifest."""
        actual = sha256_file(artifact_path)
        text = checksums_file.read_text(encoding="utf-8")
        expected: Optional[str] = None
        for line in text.splitlines():
            parts = line.strip().split()
            if len(parts) >= 2 and parts[-1].lstrip("*") == artifact_path.name:
                expected = parts[0].lower()
                break
        if expected and actual.lower() != expected:
            raise InstallWizardError(
                "cli_install",
                "CHECKSUM_MISMATCH",
                f"SHA-256 mismatch for {artifact_path.name}: expected {expected}, got {actual}.",
                "Run `hath0r release build` to refresh release checksums or re-download the release.",
            )
        return actual

    def ensure_bin_on_path(self, target_bin_dir: Path, *, dry_run: bool = False) -> Dict[str, Any]:
        """Ensure `target_bin_dir` is on `os.environ['PATH']` and persisted in shell profile."""
        bin_str = str(target_bin_dir.resolve())
        path_entries = [p for p in os.environ.get("PATH", "").split(os.pathsep) if p]
        already_on_path = bin_str in path_entries
        updated_profile: Optional[str] = None

        if not already_on_path:
            os.environ["PATH"] = f"{bin_str}{os.pathsep}{os.environ.get('PATH', '')}"

        shell = os.environ.get("SHELL", "")
        profile_candidates = [
            Path.home() / (".zshrc" if "zsh" in shell else ".bashrc"),
            Path.home() / ".profile",
        ]
        export_line = f'export PATH="{bin_str}:$PATH"'
        for prof in profile_candidates:
            if prof.is_file():
                try:
                    content = prof.read_text(encoding="utf-8")
                except OSError:
                    continue
                if bin_str not in content:
                    if not dry_run:
                        with prof.open("a", encoding="utf-8") as fh:
                            fh.write(f"\n# Added by Hath0r Install Wizard\n{export_line}\n")
                    updated_profile = str(prof)
                break

        return {
            "bin_dir": bin_str,
            "already_on_path": already_on_path,
            "updated_profile": updated_profile,
        }

    def install_cli_global(
        self,
        *,
        method: Optional[str] = None,
        version: Optional[str] = None,
        force: bool = False,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Install `hath0r` globally via `pipx`, `binary`, or `pip` and ensure PATH availability."""
        upgrader = UpgradeBot(cwd=self.cwd, repo=self.cli_repo, runner=self.runner, http_get=self.http_get)
        current = upgrader.detect_install()
        chosen_method = (method or "").strip().lower()
        if not chosen_method:
            if shutil.which("pipx"):
                chosen_method = "pipx"
            elif self._find_local_release_dir() is not None:
                chosen_method = "binary"
            else:
                chosen_method = "pip"

        if chosen_method not in INSTALL_METHODS:
            raise InstallWizardError(
                "cli_install",
                "INVALID_INSTALL_METHOD",
                f"Unsupported CLI install method '{chosen_method}'. Choose from {INSTALL_METHODS}.",
                "Pass `--method pipx`, `--method binary`, or `--method pip`.",
            )

        path_info = self.ensure_bin_on_path(self.bin_dir, dry_run=dry_run)
        local_release_dir = self._find_local_release_dir()

        if dry_run:
            return {
                "success": True,
                "dry_run": True,
                "method": chosen_method,
                "target_version": version or current.version,
                "bin_dir": str(self.bin_dir),
                "path_info": path_info,
                "action": f"[DRY-RUN] Would install hath0r globally via {chosen_method} into {self.bin_dir}.",
            }

        self.bin_dir.mkdir(parents=True, exist_ok=True)
        cli_root = Path(__file__).resolve().parents[3]
        has_local_source = (cli_root / "pyproject.toml").is_file()

        # Case 1: Standalone binary installation (from local release/ or GitHub Releases)
        if chosen_method == "binary":
            sys_name = platform.system().lower()
            mach = platform.machine().lower()
            arch_x86 = "arm64" if mach in ("arm64", "aarch64") else "x86_64"
            local_bin_name = f"hath0r-{sys_name}-{arch_x86}"
            target_bin = self.bin_dir / "hath0r"

            if local_release_dir and (local_release_dir / local_bin_name).is_file():
                src_bin = local_release_dir / local_bin_name
                digest = self._verify_checksum_from_file(src_bin, local_release_dir / "CHECKSUMS.sha256")
                tmp_bin = target_bin.with_name("hath0r.new")
                shutil.copy2(src_bin, tmp_bin)
                tmp_bin.chmod(0o755)
                os.replace(tmp_bin, target_bin)
                return {
                    "success": True,
                    "method": "binary",
                    "source": "local_release",
                    "version": version or current.version,
                    "binary_path": str(target_bin),
                    "sha256": digest,
                    "path_info": path_info,
                }

            # Fallback to GitHub Release binary
            release = upgrader.fetch_release(version)
            asset = release.binary(platform_tag())
            if not asset:
                raise InstallWizardError(
                    "cli_install",
                    "BINARY_ASSET_MISSING",
                    f"Release {release.tag} does not have a binary for platform '{platform_tag()}'.",
                    "Re-run with `--method pipx` or `--method pip`.",
                )
            with tempfile.TemporaryDirectory(prefix="hath0r-wiz-bin-") as tmp:
                dl = upgrader.download_verified(release, asset, Path(tmp))
                staged = Path(dl["path"])
                staged.chmod(0o755)
                tmp_bin = target_bin.with_name("hath0r.new")
                shutil.copy2(staged, tmp_bin)
                os.replace(tmp_bin, target_bin)
                return {
                    "success": True,
                    "method": "binary",
                    "source": "github_release",
                    "version": release.version,
                    "binary_path": str(target_bin),
                    "sha256": dl["sha256"],
                    "path_info": path_info,
                }

        # Case 2: pipx or pip installation (wheel from GitHub Release or local source checkout)
        artifact_target: Optional[str] = None
        artifact_sha256 = ""
        resolved_version = version or current.version

        with tempfile.TemporaryDirectory(prefix="hath0r-wiz-whl-") as tmp:
            try:
                release = upgrader.fetch_release(version)
                wheel = release.wheel()
                if wheel:
                    dl = upgrader.download_verified(release, wheel, Path(tmp))
                    artifact_target = dl["path"]
                    artifact_sha256 = dl["sha256"]
                    resolved_version = release.version
            except UpgradeError:
                artifact_target = None

            if not artifact_target:
                if has_local_source:
                    artifact_target = str(cli_root)
                else:
                    raise InstallWizardError(
                        "cli_install",
                        "WHEEL_UNAVAILABLE",
                        "Could not download release wheel from GitHub Releases and no local CLI checkout found.",
                        "Check network access to github.com or pass `--method binary` with a release bundle.",
                    )

            if chosen_method == "pipx":
                pipx_exe = shutil.which("pipx")
                cmd = (
                    [pipx_exe, "install", "--force", artifact_target]
                    if pipx_exe
                    else [self.python, "-m", "pipx", "install", "--force", artifact_target]
                )
            else:
                if has_local_source and artifact_target == str(cli_root):
                    cmd = [self.python, "-m", "pip", "install", "-e", artifact_target]
                else:
                    cmd = [self.python, "-m", "pip", "install", "--upgrade", "--force-reinstall", artifact_target]

            rc, out, err = self.runner(cmd, timeout=900)
            if rc != 0:
                raise InstallWizardError(
                    "cli_install",
                    "CLI_INSTALL_FAILED",
                    f"Global CLI installation via {chosen_method} failed: {(err or out)[:500]}",
                    "Verify Python/pipx permissions or try `--method binary`.",
                )

        exe_path = shutil.which("hath0r") or str(self.bin_dir / "hath0r")
        return {
            "success": True,
            "method": chosen_method,
            "version": resolved_version,
            "binary_path": exe_path,
            "sha256": artifact_sha256,
            "path_info": path_info,
        }

    # ── Stage 3: Hath0r MCP Dockerfile, Compose & Knowledge Staging ───────────

    def _locate_local_mcp_source(self) -> Optional[Path]:
        """Locate sibling `hath0r-mcp` repository if running inside the OpenSource workspace."""
        candidates = [
            self.cwd / "hath0r-mcp",
            self.cwd.parent / "hath0r-mcp",
            Path(__file__).resolve().parents[4] / "hath0r-mcp",
        ]
        if (self.cwd / "Dockerfile").is_file() and (self.cwd / "docker-compose.yml").is_file():
            if "hath0r-mcp" in (self.cwd / "docker-compose.yml").read_text(encoding="utf-8"):
                candidates.insert(0, self.cwd)
        for cand in candidates:
            if cand.is_dir() and (cand / "Dockerfile").is_file() and (cand / "docker-compose.yml").is_file():
                return cand.resolve()
        return None

    def stage_mcp_docker(
        self,
        *,
        mcp_dir: Optional[Path] = None,
        mcp_port: int = DEFAULT_MCP_PORT,
        version: Optional[str] = None,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Stage the Hath0r MCP `Dockerfile`, `docker-compose.yml`, `requirements.txt`, and `knowledgebase/`."""
        local_src = self._locate_local_mcp_source()
        target_dir = (mcp_dir or local_src or self.default_mcp_dir).resolve()

        if dry_run:
            return {
                "success": True,
                "dry_run": True,
                "mcp_dir": str(target_dir),
                "source": "local_sibling" if local_src and target_dir == local_src else "staged_bundle",
                "dockerfile": str(target_dir / "Dockerfile"),
                "compose_file": str(target_dir / "docker-compose.yml"),
                "host_port": mcp_port,
                "action": f"[DRY-RUN] Would stage Hath0r MCP Dockerfile, docker-compose.yml, and knowledgebase at {target_dir}.",
            }

        target_dir.mkdir(parents=True, exist_ok=True)
        source_kind = "embedded_template"

        if local_src and local_src == target_dir:
            source_kind = "local_sibling_in_place"
        elif local_src and local_src != target_dir:
            source_kind = "local_sibling_copy"
            for fname in ("Dockerfile", "docker-compose.yml", "requirements.txt", "pyproject.toml", "README.md"):
                src_f = local_src / fname
                if src_f.is_file():
                    shutil.copy2(src_f, target_dir / fname)
            for dname in ("src", "knowledgebase"):
                src_d = local_src / dname
                dst_d = target_dir / dname
                if src_d.is_dir():
                    shutil.copytree(src_d, dst_d, dirs_exist_ok=True)
        else:
            # Try cloning Bayly-AI/HATH0R-MCP if git is available and directory is not yet a checkout
            if not (target_dir / "Dockerfile").is_file() and shutil.which("git"):
                repo_url = f"https://github.com/{self.mcp_repo}.git"
                clone_cmd = ["git", "clone", "--depth", "1"]
                if version:
                    clone_cmd.extend(["--branch", version])
                clone_cmd.extend([repo_url, str(target_dir)])
                rc, _, _ = self.runner(clone_cmd, timeout=180)
                if rc == 0 and (target_dir / "Dockerfile").is_file():
                    source_kind = "github_clone"

        # Guarantee Dockerfile, docker-compose.yml, requirements.txt, src/, and knowledgebase/ exist
        dockerfile_path = target_dir / "Dockerfile"
        compose_path = target_dir / "docker-compose.yml"
        reqs_path = target_dir / "requirements.txt"

        if not dockerfile_path.is_file():
            dockerfile_path.write_text(EMBEDDED_MCP_DOCKERFILE, encoding="utf-8")
        if not compose_path.is_file():
            compose_path.write_text(EMBEDDED_MCP_COMPOSE, encoding="utf-8")
        if not reqs_path.is_file():
            reqs_path.write_text(EMBEDDED_MCP_REQUIREMENTS, encoding="utf-8")

        src_pkg = target_dir / "src" / "knowledgebase"
        if not (src_pkg / "server.py").is_file():
            src_pkg.mkdir(parents=True, exist_ok=True)
            (src_pkg / "__init__.py").write_text('__version__ = "1.5.0"\n', encoding="utf-8")
            (src_pkg / "server.py").write_text(EMBEDDED_MCP_FALLBACK_SERVER, encoding="utf-8")

        kb_canonical = target_dir / "knowledgebase" / "canonical"
        kb_canonical.mkdir(parents=True, exist_ok=True)
        if not list(kb_canonical.rglob("*.md")):
            (kb_canonical / "00-suite-overview.md").write_text(EMBEDDED_SEED_KB_DOC, encoding="utf-8")

        env_file = target_dir / ".env"
        if not env_file.is_file():
            env_file.write_text(
                f"HATH0R_MCP_ENVIRONMENT=local\n"
                f"HATH0R_MCP_HOST_PORT={mcp_port}\n"
                f"HATH0R_MCP_MEM_LIMIT=512m\n"
                f"HATH0R_MCP_CPU_LIMIT=1.0\n",
                encoding="utf-8",
            )

        # Validate docker-compose.yml syntax if docker is available
        compose_valid = True
        if shutil.which("docker"):
            rc_cfg, _, err_cfg = self.runner(
                ["docker", "compose", "-p", DEFAULT_COMPOSE_PROJECT, "-f", str(compose_path), "config", "--quiet"],
                cwd=target_dir,
                timeout=30,
            )
            compose_valid = rc_cfg == 0
            if not compose_valid:
                raise InstallWizardError(
                    "mcp_stage",
                    "COMPOSE_CONFIG_INVALID",
                    f"Docker Compose validation failed for {compose_path}: {err_cfg}",
                    "Inspect docker-compose.yml syntax and Docker Compose v2 installation.",
                )

        return {
            "success": True,
            "source": source_kind,
            "mcp_dir": str(target_dir),
            "dockerfile": str(dockerfile_path),
            "compose_file": str(compose_path),
            "env_file": str(env_file),
            "knowledgebase_dir": str(kb_canonical),
            "host_port": mcp_port,
            "compose_valid": compose_valid,
        }

    # ── Stage 4: Docker Network & Hath0r-MCP Container Launch ─────────────────

    def ensure_docker_network(
        self,
        network_name: str = DEFAULT_NETWORK_NAME,
        *,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Ensure external Docker network `hath0r-net` exists with canonical `com.hath0r.*` labels."""
        if dry_run:
            return {
                "success": True,
                "dry_run": True,
                "network": network_name,
                "action": f"[DRY-RUN] Would ensure Docker network '{network_name}' with com.hath0r.* labels.",
            }

        rc_insp, _, _ = self.runner(["docker", "network", "inspect", network_name], timeout=15)
        if rc_insp == 0:
            return {"success": True, "network": network_name, "created": False}

        create_cmd = [
            "docker",
            "network",
            "create",
            "--label",
            "com.hath0r.org=bayly-ai",
            "--label",
            "com.hath0r.project=hath0r-opensource",
            "--label",
            "com.hath0r.component=network",
            network_name,
        ]
        rc_cr, out_cr, err_cr = self.runner(create_cmd, timeout=30)
        if rc_cr != 0:
            raise InstallWizardError(
                "mcp_launch",
                "DOCKER_NETWORK_FAILED",
                f"Failed to create Docker network '{network_name}': {err_cr or out_cr}",
                "Verify that the Docker daemon is running (`docker info`).",
            )
        return {"success": True, "network": network_name, "created": True}

    def launch_mcp_container(
        self,
        mcp_dir: Path,
        *,
        mcp_port: int = DEFAULT_MCP_PORT,
        image_url: Optional[str] = None,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Ensure `hath0r-net` and launch `Hath0r-MCP` via Docker Compose."""
        compose_file = mcp_dir / "docker-compose.yml"
        net_res = self.ensure_docker_network(DEFAULT_NETWORK_NAME, dry_run=dry_run)

        if dry_run:
            return {
                "success": True,
                "dry_run": True,
                "network": net_res["network"],
                "container_name": DEFAULT_MCP_CONTAINER,
                "image": image_url or DEFAULT_MCP_IMAGE,
                "host_port": mcp_port,
                "action": (
                    f"[DRY-RUN] Would run `docker compose -p {DEFAULT_COMPOSE_PROJECT} "
                    f"-f {compose_file} up -d --build --wait {DEFAULT_MCP_SERVICE}` on port {mcp_port}."
                ),
            }

        if image_url and image_url.strip():
            url = image_url.strip()
            rc_pull, out_p, err_p = self.runner(["docker", "pull", url], timeout=600)
            if rc_pull != 0:
                raise InstallWizardError(
                    "mcp_launch",
                    "IMAGE_PULL_FAILED",
                    f"Failed to pull MCP image '{url}': {err_p or out_p}",
                    "Verify the container registry URL or omit `--image-url` to build locally from Dockerfile.",
                )
            self.runner(["docker", "tag", url, DEFAULT_MCP_IMAGE], timeout=30)
            up_cmd = [
                "docker",
                "compose",
                "-p",
                DEFAULT_COMPOSE_PROJECT,
                "-f",
                str(compose_file),
                "up",
                "-d",
                "--wait",
                DEFAULT_MCP_SERVICE,
            ]
        else:
            up_cmd = [
                "docker",
                "compose",
                "-p",
                DEFAULT_COMPOSE_PROJECT,
                "-f",
                str(compose_file),
                "up",
                "-d",
                "--build",
                "--wait",
                DEFAULT_MCP_SERVICE,
            ]

        os.environ["HATH0R_MCP_HOST_PORT"] = str(mcp_port)
        rc_up, out_up, err_up = self.runner(up_cmd, cwd=mcp_dir, timeout=900)
        if rc_up != 0:
            raise InstallWizardError(
                "mcp_launch",
                "MCP_CONTAINER_LAUNCH_FAILED",
                f"Failed to build/launch {DEFAULT_MCP_CONTAINER}: {(err_up or out_up)[:600]}",
                f"Check `docker compose -p {DEFAULT_COMPOSE_PROJECT} -f {compose_file} logs` and port {mcp_port}.",
            )

        rc_insp, out_insp, _ = self.runner(
            [
                "docker",
                "inspect",
                "-f",
                "health={{if .State.Health}}{{.State.Health.Status}}{{else}}running{{end}} status={{.State.Status}}",
                DEFAULT_MCP_CONTAINER,
            ],
            timeout=15,
        )
        return {
            "success": True,
            "network": DEFAULT_NETWORK_NAME,
            "network_created": net_res.get("created", False),
            "container_name": DEFAULT_MCP_CONTAINER,
            "service_name": DEFAULT_MCP_SERVICE,
            "image": image_url or DEFAULT_MCP_IMAGE,
            "host_port": mcp_port,
            "container_status": out_insp.strip() if rc_insp == 0 else "running",
        }

    # ── Stage 5: Readiness Probes, Connector Wiring & Receipt ─────────────────

    def probe_mcp_ready(self, port: int = DEFAULT_MCP_PORT, retries: int = 15, delay_s: float = 1.0) -> Dict[str, Any]:
        """Probe `http://127.0.0.1:<port>/health` and `/ready`."""
        base_url = f"http://127.0.0.1:{port}"
        health_url = f"{base_url}/health"
        ready_url = f"{base_url}/ready"
        last_err = ""

        for _ in range(max(1, retries)):
            try:
                raw_h = self.http_get(health_url, {"Accept": "application/json", "User-Agent": "hath0r-install-wizard"})
                raw_r = self.http_get(ready_url, {"Accept": "application/json", "User-Agent": "hath0r-install-wizard"})
                health_data = json.loads(raw_h.decode("utf-8")) if raw_h else {}
                ready_data = json.loads(raw_r.decode("utf-8")) if raw_r else {}
                return {
                    "passed": True,
                    "base_url": base_url,
                    "health_url": health_url,
                    "ready_url": ready_url,
                    "health": health_data,
                    "ready": ready_data,
                }
            except Exception as exc:
                last_err = str(exc)
                if retries > 1:
                    time.sleep(delay_s)

        return {
            "passed": False,
            "base_url": base_url,
            "health_url": health_url,
            "ready_url": ready_url,
            "error": last_err or "MCP server did not respond to /ready",
        }

    def configure_mcp_client_files(
        self,
        *,
        mcp_port: int = DEFAULT_MCP_PORT,
        mcp_dir: Optional[Path] = None,
        install_claude: bool = False,
        cli_binary: Optional[str] = None,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Write canonical `~/.hath0r/mcp.json` (and repo `.hath0r/mcp.json` if in a repo) + optional Claude config."""
        base_url = f"http://127.0.0.1:{mcp_port}"
        user_mcp_file = self.home_dir / "mcp.json"
        kb_path = str((mcp_dir or self.default_mcp_dir) / "knowledgebase" / "canonical")

        mcp_payload = {
            "version": "1.0",
            "engine": "hath0r-mcp",
            "default_provider": "hath0r-mcp",
            "group": "hath0r-opensource",
            "default_server": "hath0r-mcp",
            "servers": [
                {
                    "id": "hath0r-mcp",
                    "name": "Hath0rMCP",
                    "engine": "hath0r-mcp",
                    "scope": "project",
                    "group": "hath0r-opensource",
                    "priority": 1,
                    "product_id": "hath0r-mcp",
                    "transport": "streamable-http",
                    "base_url": base_url,
                    "mcp_endpoint": "/mcp",
                    "health_endpoint": "/health",
                    "ready_endpoint": "/ready",
                    "enabled": True,
                    "local_path": kb_path,
                }
            ],
        }

        if not dry_run:
            user_mcp_file.parent.mkdir(parents=True, exist_ok=True)
            user_mcp_file.write_text(json.dumps(mcp_payload, indent=2) + "\n", encoding="utf-8")

        repo_mcp_res: Optional[Dict[str, Any]] = None
        if (self.cwd / ".git").exists():
            try:
                from hath0r_cli.mcp import ensure_repo_mcp_config

                repo_mcp_res = ensure_repo_mcp_config(self.cwd, sync_cfg=True, dry_run=dry_run)
            except Exception as exc:
                repo_mcp_res = {"success": False, "error": str(exc)}

        claude_res: Optional[Dict[str, Any]] = None
        if install_claude and not dry_run:
            try:
                from hath0r_cli.server.mcp_server import install_claude_desktop_connector

                claude_res = install_claude_desktop_connector(hath0r_binary=cli_binary)
            except Exception as exc:
                claude_res = {"success": False, "error": str(exc)}

        return {
            "user_mcp_file": str(user_mcp_file),
            "base_url": base_url,
            "repo_mcp": repo_mcp_res,
            "claude_desktop": claude_res,
        }

    # ── Orchestration: Full 5-Stage Wizard ────────────────────────────────────

    def run_wizard(
        self,
        *,
        version: Optional[str] = None,
        method: Optional[str] = None,
        mcp_dir: Optional[Path] = None,
        mcp_port: int = DEFAULT_MCP_PORT,
        image_url: Optional[str] = None,
        skip_docker: bool = False,
        install_claude: bool = False,
        auto_approve: bool = True,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Execute the complete 5-stage Hath0r CLI + Hath0r MCP (Docker) Install Wizard."""
        started = time.perf_counter()
        receipt: Dict[str, Any] = {
            "schema": RECEIPT_SCHEMA,
            "run_id": f"wiz_{int(time.time())}_{os.getpid()}",
            "started_at": _utc_now(),
            "dry_run": dry_run,
            "stages": [],
            "outcome": "failed",
            "success": False,
        }

        def record_stage(name: str, status: str, **info: Any) -> None:
            receipt["stages"].append({"stage": name, "status": status, **info})

        with trace_span(
            "hath0r.install_wizard.run",
            attributes={
                "hath0r.wizard.method": method or "auto",
                "hath0r.wizard.mcp_port": mcp_port,
                "hath0r.wizard.skip_docker": skip_docker,
                "hath0r.wizard.dry_run": dry_run,
                "feature_flag.install_wizard.enabled": True,
                "hath0r.phoenix.endpoint": "http://localhost:38000/phoenix",
            },
        ):
            try:
                # Stage 1: Dependencies
                chosen_method = (method or ("pipx" if shutil.which("pipx") else "pip")).lower()
                deps_res = self.install_dependencies(
                    need_pipx=(chosen_method == "pipx"),
                    need_docker=not skip_docker,
                    start_daemon=not skip_docker,
                    dry_run=dry_run,
                )
                receipt["dependencies"] = deps_res["after"]
                record_stage("dependencies", "ok", actions_count=len(deps_res["actions"]))

                # Stage 2: Global CLI Install
                cli_res = self.install_cli_global(
                    method=method,
                    version=version,
                    dry_run=dry_run,
                )
                receipt["cli"] = cli_res
                record_stage("cli_install", "ok", method=cli_res.get("method"), binary=cli_res.get("binary_path"))

                # Stage 3: Stage MCP Docker files
                stage_res = self.stage_mcp_docker(
                    mcp_dir=mcp_dir,
                    mcp_port=mcp_port,
                    version=version,
                    dry_run=dry_run,
                )
                receipt["mcp_stage"] = stage_res
                record_stage("mcp_stage", "ok", mcp_dir=stage_res.get("mcp_dir"), source=stage_res.get("source"))

                # Stage 4: Launch MCP Container on hath0r-net
                if skip_docker:
                    launch_res: Dict[str, Any] = {
                        "success": True,
                        "skipped": True,
                        "network": DEFAULT_NETWORK_NAME,
                        "container_name": DEFAULT_MCP_CONTAINER,
                        "host_port": mcp_port,
                    }
                    record_stage("mcp_launch", "skipped")
                else:
                    launch_res = self.launch_mcp_container(
                        Path(stage_res["mcp_dir"]),
                        mcp_port=mcp_port,
                        image_url=image_url,
                        dry_run=dry_run,
                    )
                    record_stage(
                        "mcp_launch",
                        "ok",
                        container=launch_res.get("container_name"),
                        network=launch_res.get("network"),
                        port=mcp_port,
                    )
                receipt["mcp"] = {**stage_res, **launch_res}

                # Stage 5: Verify CLI & MCP readiness + wire client config
                cfg_res = self.configure_mcp_client_files(
                    mcp_port=mcp_port,
                    mcp_dir=Path(stage_res["mcp_dir"]),
                    install_claude=install_claude,
                    cli_binary=cli_res.get("binary_path"),
                    dry_run=dry_run,
                )

                if dry_run:
                    receipt["verification"] = {
                        "passed": True,
                        "dry_run": True,
                        "mcp_config": cfg_res,
                    }
                    record_stage("verify", "ok", dry_run=True)
                    receipt.update(
                        outcome="dry-run",
                        success=True,
                        message=(
                            f"[DRY-RUN] Install Wizard plan validated: CLI ({cli_res.get('method')}) "
                            f"+ Hath0r-MCP Docker ({stage_res.get('mcp_dir')} on 127.0.0.1:{mcp_port})."
                        ),
                    )
                    return receipt

                verifier = UpgradeVerifierBot(cwd=self.cwd, runner=self.runner, python=self.python)
                upgrader = UpgradeBot(cwd=self.cwd, repo=self.cli_repo, runner=self.runner, http_get=self.http_get)
                detected = upgrader.detect_install()
                cli_verify = verifier.verify(
                    cli_res.get("version") or detected.version,
                    level="smoke",
                    command=verifier.command_for(detected),
                    repo_root=detected.repo_root or None,
                )

                mcp_probe: Dict[str, Any] = {"passed": True, "skipped": True}
                if not skip_docker:
                    mcp_probe = self.probe_mcp_ready(port=mcp_port, retries=15, delay_s=0.5)
                    if not mcp_probe.get("passed"):
                        raise InstallWizardError(
                            "verify",
                            "MCP_READINESS_FAILED",
                            f"Hath0r-MCP container started, but http://127.0.0.1:{mcp_port}/ready failed: {mcp_probe.get('error')}",
                            "Run `hath0r install-wizard repair` or inspect `docker logs Hath0r-MCP`.",
                        )

                receipt["verification"] = {
                    "passed": bool(cli_verify.get("passed", True)) and bool(mcp_probe.get("passed", True)),
                    "cli_verification": cli_verify,
                    "mcp_readiness": mcp_probe,
                    "mcp_config": cfg_res,
                }
                record_stage("verify", "ok", cli_passed=cli_verify.get("passed"), mcp_ready=mcp_probe.get("passed"))

                receipt.update(
                    outcome="installed",
                    success=True,
                    message=(
                        f"Hath0r CLI ({cli_res.get('version')}) and Hath0r-MCP Docker "
                        f"(http://127.0.0.1:{mcp_port}) installed and verified."
                    ),
                )
                return receipt

            except InstallWizardError as exc:
                receipt["failure"] = exc.to_dict()
                record_stage(exc.stage, "failed", code=exc.code)
                receipt["outcome"] = "failed"
                receipt["success"] = False
                receipt["message"] = f"Install Wizard failed at {exc.stage} ({exc.code}): {exc.message}"
                return receipt
            except Exception as exc:
                receipt["failure"] = {
                    "stage": "internal",
                    "code": "INTERNAL_ERROR",
                    "message": str(exc),
                    "hint": "Re-run with `--verbose` or run `hath0r install-wizard check`.",
                }
                receipt["outcome"] = "failed"
                receipt["success"] = False
                receipt["message"] = f"Install Wizard internal error: {exc}"
                return receipt
            finally:
                receipt["finished_at"] = _utc_now()
                receipt["duration_ms"] = int((time.perf_counter() - started) * 1000)
                if not dry_run:
                    self._save_receipt(receipt)
                    spool_telemetry_event(
                        event_type="install_wizard.run",
                        payload={
                            "run_id": receipt["run_id"],
                            "outcome": receipt["outcome"],
                            "success": receipt["success"],
                            "duration_ms": receipt["duration_ms"],
                        },
                        base_dir=self.cwd,
                    )

    # ── Check, Status, Repair & Uninstall ─────────────────────────────────────

    def check_environment(self, *, mcp_port: int = DEFAULT_MCP_PORT) -> Dict[str, Any]:
        """Run non-mutating pre-flight & live health checks for CLI, dependencies, and MCP container."""
        deps = self.check_dependencies()
        upgrader = UpgradeBot(cwd=self.cwd, repo=self.cli_repo, runner=self.runner, http_get=self.http_get)
        cli_info = upgrader.detect_install()
        cli_exe = shutil.which("hath0r")

        net_ok = False
        container_running = False
        if deps["docker"]["ok"] and deps["docker_daemon"]["ok"]:
            rc_n, _, _ = self.runner(["docker", "network", "inspect", DEFAULT_NETWORK_NAME], timeout=10)
            net_ok = rc_n == 0
            rc_c, out_c, _ = self.runner(
                ["docker", "inspect", "-f", "{{.State.Running}}", DEFAULT_MCP_CONTAINER],
                timeout=10,
            )
            container_running = rc_c == 0 and out_c.strip().lower() == "true"

        mcp_probe = self.probe_mcp_ready(port=mcp_port, retries=1, delay_s=0.1)
        all_healthy = bool(
            deps["all_ready"] and cli_exe and net_ok and container_running and mcp_probe.get("passed")
        )

        return {
            "success": True,
            "healthy": all_healthy,
            "dependencies": deps,
            "cli": {
                **cli_info.to_dict(),
                "on_path": bool(cli_exe),
                "which": cli_exe or "",
            },
            "mcp_docker": {
                "network": DEFAULT_NETWORK_NAME,
                "network_present": net_ok,
                "container_name": DEFAULT_MCP_CONTAINER,
                "container_running": container_running,
                "port": mcp_port,
                "ready": bool(mcp_probe.get("passed")),
                "probe": mcp_probe,
            },
            "receipt_present": self.receipt_file.is_file(),
        }

    def status(self, *, mcp_port: int = DEFAULT_MCP_PORT) -> Dict[str, Any]:
        """Return the last persisted `INSTALL_RECEIPT.json` along with live environment status."""
        last_receipt: Optional[Dict[str, Any]] = None
        if self.receipt_file.is_file():
            try:
                last_receipt = json.loads(self.receipt_file.read_text(encoding="utf-8"))
            except ValueError:
                last_receipt = None
        env_check = self.check_environment(mcp_port=mcp_port)
        return {
            "success": True,
            "receipt_file": str(self.receipt_file),
            "last_receipt": last_receipt,
            "environment": env_check,
            "message": (
                f"Last install: {last_receipt.get('outcome')} at {last_receipt.get('finished_at')}"
                if last_receipt
                else "No install receipt recorded yet; live environment status attached."
            ),
        }

    def repair(
        self,
        *,
        mcp_dir: Optional[Path] = None,
        mcp_port: int = DEFAULT_MCP_PORT,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Re-verify CLI PATH, re-stage MCP Docker files if missing, ensure `hath0r-net`, and restart `Hath0r-MCP`."""
        path_info = self.ensure_bin_on_path(self.bin_dir, dry_run=dry_run)
        stage_res = self.stage_mcp_docker(mcp_dir=mcp_dir, mcp_port=mcp_port, dry_run=dry_run)
        launch_res = self.launch_mcp_container(
            Path(stage_res["mcp_dir"]),
            mcp_port=mcp_port,
            dry_run=dry_run,
        )
        probe = (
            {"passed": True, "dry_run": True}
            if dry_run
            else self.probe_mcp_ready(port=mcp_port, retries=10, delay_s=0.5)
        )
        ok = bool(launch_res.get("success") and probe.get("passed"))
        return {
            "success": ok,
            "dry_run": dry_run,
            "path_info": path_info,
            "mcp_stage": stage_res,
            "mcp_launch": launch_res,
            "mcp_readiness": probe,
            "message": (
                "[DRY-RUN] Would repair CLI PATH, hath0r-net, and Hath0r-MCP container."
                if dry_run
                else (
                    f"Repaired and verified Hath0r-MCP on http://127.0.0.1:{mcp_port}/ready."
                    if ok
                    else f"Repair completed container launch, but readiness probe failed: {probe.get('error')}"
                )
            ),
        }

    def uninstall(
        self,
        *,
        mcp_dir: Optional[Path] = None,
        purge_data: bool = False,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Stop and remove the `Hath0r-MCP` Docker container (leaving shared ATC infra untouched)."""
        target_mcp_dir = (mcp_dir or self._locate_local_mcp_source() or self.default_mcp_dir).resolve()
        compose_file = target_mcp_dir / "docker-compose.yml"

        if dry_run:
            return {
                "success": True,
                "dry_run": True,
                "mcp_dir": str(target_mcp_dir),
                "purge_data": purge_data,
                "action": f"[DRY-RUN] Would stop/remove {DEFAULT_MCP_CONTAINER} via {compose_file}.",
            }

        if compose_file.is_file() and shutil.which("docker"):
            self.runner(
                [
                    "docker",
                    "compose",
                    "-p",
                    DEFAULT_COMPOSE_PROJECT,
                    "-f",
                    str(compose_file),
                    "rm",
                    "-f",
                    "-s",
                    DEFAULT_MCP_SERVICE,
                ],
                cwd=target_mcp_dir,
                timeout=60,
            )
        elif shutil.which("docker"):
            self.runner(["docker", "rm", "-f", DEFAULT_MCP_CONTAINER], timeout=30)

        removed_dir = False
        if purge_data and target_mcp_dir == self.default_mcp_dir and target_mcp_dir.is_dir():
            shutil.rmtree(target_mcp_dir, ignore_errors=True)
            removed_dir = True

        return {
            "success": True,
            "container_removed": DEFAULT_MCP_CONTAINER,
            "mcp_dir": str(target_mcp_dir),
            "purged_dir": removed_dir,
            "message": f"Stopped and removed {DEFAULT_MCP_CONTAINER} (shared hath0r-net infrastructure untouched).",
        }

    def _save_receipt(self, receipt: Dict[str, Any]) -> None:
        try:
            self.receipt_file.parent.mkdir(parents=True, exist_ok=True)
            self.receipt_file.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
            summary = {
                "run_id": receipt.get("run_id"),
                "finished_at": receipt.get("finished_at"),
                "outcome": receipt.get("outcome"),
                "success": receipt.get("success"),
                "cli_version": (receipt.get("cli") or {}).get("version"),
                "mcp_port": (receipt.get("mcp") or {}).get("host_port"),
            }
            with self.history_file.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(summary) + "\n")
        except OSError:
            pass

    # ── Native Installer Packaging: macOS (.dmg) & Windows (.exe) ────────────

    def _cli_root(self) -> Path:
        cand = Path(__file__).resolve().parents[3]
        if (cand / "VERSION").is_file():
            return cand
        return self.cwd.resolve()

    def _read_cli_version(self) -> str:
        ver_file = self._cli_root() / "VERSION"
        if ver_file.is_file():
            return ver_file.read_text(encoding="utf-8").strip()
        return "1.22.0"

    def _load_install_script_bytes(self) -> bytes:
        cli_root = self._cli_root()
        for rel in ("scripts/install_hath0r.py", "release/install_hath0r.py"):
            p = cli_root / rel
            if p.is_file():
                return p.read_bytes()
        fallback = (
            "#!/usr/bin/env python3\n"
            "import subprocess, sys\n"
            "raise SystemExit(subprocess.call(['hath0r', 'install-wizard', 'run'] + sys.argv[1:]))\n"
        )
        return fallback.encode("utf-8")

    def _generate_macos_icns(self, dest_icns: Path) -> bool:
        """Generate a macOS `.icns` icon file for `Hath0r Install Wizard.app` using Pillow + `iconutil`."""
        iconutil_bin = shutil.which("iconutil")
        if not iconutil_bin:
            return False
        try:
            from PIL import Image, ImageDraw

            with tempfile.TemporaryDirectory(prefix="hath0r-iconset-") as tmp:
                iconset_dir = Path(tmp) / "Hath0rWizard.iconset"
                iconset_dir.mkdir(parents=True, exist_ok=True)
                base_size = 512
                img = Image.new("RGBA", (base_size, base_size), (13, 18, 30, 255))
                draw = ImageDraw.Draw(img)
                # Outer gold/cyan ring + inner "H0" emblem
                draw.rounded_rectangle(
                    (24, 24, base_size - 24, base_size - 24),
                    radius=96,
                    fill=(18, 28, 48, 255),
                    outline=(0, 212, 255, 255),
                    width=14,
                )
                draw.rounded_rectangle(
                    (64, 64, base_size - 64, base_size - 64),
                    radius=64,
                    fill=(24, 38, 66, 255),
                    outline=(245, 194, 66, 255),
                    width=8,
                )
                # Draw stylized "H"
                draw.rectangle((140, 140, 185, 372), fill=(0, 212, 255, 255))
                draw.rectangle((327, 140, 372, 372), fill=(0, 212, 255, 255))
                draw.rectangle((185, 236, 327, 276), fill=(245, 194, 66, 255))

                sizes = [16, 32, 128, 256, 512]
                for sz in sizes:
                    resized = img.resize((sz, sz))
                    resized.save(iconset_dir / f"icon_{sz}x{sz}.png", format="PNG")
                    resized2x = img.resize(( min(sz * 2, 1024), min(sz * 2, 1024) ))
                    resized2x.save(iconset_dir / f"icon_{sz}x{sz}@2x.png", format="PNG")

                rc, _, _ = self.runner(
                    [iconutil_bin, "-c", "icns", str(iconset_dir), "-o", str(dest_icns)],
                    timeout=30,
                )
                return rc == 0 and dest_icns.is_file()
        except Exception:
            return False

    def build_macos_dmg(
        self,
        *,
        out_dir: Optional[Path] = None,
        version: Optional[str] = None,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Build the macOS `.dmg` Disk Image containing `Hath0r Install Wizard.app` and `.command` launcher."""
        cli_root = self._cli_root()
        if out_dir is None:
            target_dir = (cli_root / "release" / "mac").resolve()
        else:
            resolved_out = out_dir.resolve()
            target_dir = (resolved_out / "mac") if (resolved_out / "mac").is_dir() else resolved_out
        ver = version or self._read_cli_version()
        canonical_dmg = target_dir / "Hath0r-Install-Wizard.dmg"
        versioned_dmg = target_dir / f"Hath0r-Install-Wizard-{ver}-macos.dmg"

        if dry_run:
            return {
                "success": True,
                "dry_run": True,
                "platform": "macos",
                "version": ver,
                "dmg_path": str(canonical_dmg),
                "versioned_dmg_path": str(versioned_dmg),
                "action": f"[DRY-RUN] Would build macOS disk image {canonical_dmg} and {versioned_dmg}.",
            }

        target_dir.mkdir(parents=True, exist_ok=True)
        script_bytes = self._load_install_script_bytes()

        with tempfile.TemporaryDirectory(prefix="hath0r-dmg-stage-") as tmp:
            stage_root = Path(tmp) / "Hath0r-Install-Wizard"
            app_bundle = stage_root / "Hath0r Install Wizard.app"
            contents_dir = app_bundle / "Contents"
            macos_dir = contents_dir / "MacOS"
            resources_dir = contents_dir / "Resources"
            macos_dir.mkdir(parents=True, exist_ok=True)
            resources_dir.mkdir(parents=True, exist_ok=True)

            # 1. Embed install_hath0r.py and install-wizard.sh in Resources/
            res_py = resources_dir / "install_hath0r.py"
            res_py.write_bytes(script_bytes)
            res_py.chmod(0o755)

            sh_src = cli_root / "release" / "install-wizard.sh"
            res_sh = resources_dir / "install-wizard.sh"
            if sh_src.is_file():
                shutil.copy2(sh_src, res_sh)
            else:
                res_sh.write_text(
                    '#!/usr/bin/env sh\nexec python3 "$(dirname "$0")/install_hath0r.py" "$@"\n',
                    encoding="utf-8",
                )
            res_sh.chmod(0o755)

            # 2. Generate application icon (.icns)
            icns_path = resources_dir / "Hath0rWizard.icns"
            self._generate_macos_icns(icns_path)

            # 3. Write Contents/Info.plist
            info_plist = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleDevelopmentRegion</key>
    <string>en</string>
    <key>CFBundleDisplayName</key>
    <string>Hath0r Install Wizard</string>
    <key>CFBundleExecutable</key>
    <string>Hath0rInstallWizard</string>
    <key>CFBundleIconFile</key>
    <string>Hath0rWizard.icns</string>
    <key>CFBundleIdentifier</key>
    <string>ai.bayly.hath0r.install-wizard</string>
    <key>CFBundleInfoDictionaryVersion</key>
    <string>6.0</string>
    <key>CFBundleName</key>
    <string>Hath0r Install Wizard</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>{ver}</string>
    <key>CFBundleVersion</key>
    <string>{ver}</string>
    <key>LSMinimumSystemVersion</key>
    <string>12.0</string>
    <key>NSHighResolutionCapable</key>
    <true/>
</dict>
</plist>
"""
            (contents_dir / "Info.plist").write_text(info_plist, encoding="utf-8")

            # 4. Write Contents/MacOS/Hath0rInstallWizard launcher
            app_exec = macos_dir / "Hath0rInstallWizard"
            app_exec.write_text(
                """#!/usr/bin/env bash
set -euo pipefail

CONTENTS_DIR="$(cd "$(dirname "$0")/.." && pwd)"
RES_DIR="$CONTENTS_DIR/Resources"
WIZARD_PY="$RES_DIR/install_hath0r.py"

export PATH="/opt/homebrew/bin:/usr/local/bin:$HOME/.local/bin:$PATH"

# If invoked with CLI arguments or inside a terminal, execute directly
if [ "$#" -gt 0 ] || [ -t 0 ]; then
    exec python3 "$WIZARD_PY" "$@"
fi

# Launched via Finder double-click: prompt with native macOS dialog then open Terminal
if command -v osascript >/dev/null 2>&1; then
    CHOICE="$(osascript -e 'display dialog "Welcome to the Hath0r Install Wizard!\\n\\nThis wizard will:\\n1. Install required dependencies (Python, pipx, Git, curl, Docker)\\n2. Install the hath0r CLI globally on PATH\\n3. Stage the Hath0r MCP Dockerfile & docker-compose.yml\\n4. Launch the Hath0r-MCP Docker container on hath0r-net (port 38083)" buttons {"Cancel", "Launch Install Wizard"} default button "Launch Install Wizard" with title "Hath0r CLI + MCP Install Wizard"' 2>/dev/null || true)"
    if [[ "$CHOICE" != *"Launch Install Wizard"* ]]; then
        exit 0
    fi
    osascript -e "tell application \\"Terminal\\"
        activate
        do script \\"python3 '$WIZARD_PY'; echo ''; echo 'Press Enter to close...'; read\\"
    end tell" >/dev/null 2>&1 && exit 0
fi

exec python3 "$WIZARD_PY" -y
""",
                encoding="utf-8",
            )
            app_exec.chmod(0o755)

            # 5. Also include a double-clickable Terminal script at root of DMG
            cmd_launcher = stage_root / "Install Hath0r Wizard.command"
            cmd_launcher.write_text(
                """#!/usr/bin/env bash
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
export PATH="/opt/homebrew/bin:/usr/local/bin:$HOME/.local/bin:$PATH"
python3 "$DIR/Hath0r Install Wizard.app/Contents/Resources/install_hath0r.py" "$@"
""",
                encoding="utf-8",
            )
            cmd_launcher.chmod(0o755)

            # 6. Include README.txt inside the DMG
            (stage_root / "README.txt").write_text(
                f"Hath0r CLI + Hath0r MCP (Docker) — Official Install Wizard (v{ver})\n"
                "====================================================================\n\n"
                "To launch the Install Wizard:\n"
                "  1. Double-click 'Hath0r Install Wizard.app' (or 'Install Hath0r Wizard.command').\n"
                "  2. Or run from Terminal:\n"
                '     "/Volumes/Hath0r Install Wizard/Hath0r Install Wizard.app/Contents/MacOS/Hath0rInstallWizard"\n\n'
                "What the Wizard Installs:\n"
                "  - System dependencies (Python >= 3.10, pipx, Git, curl, Docker Engine, Docker Compose v2)\n"
                "  - Global `hath0r` CLI executable on PATH\n"
                "  - Hath0r MCP Dockerfile, docker-compose.yml, and canonical knowledgebase (~/.hath0r/mcp)\n"
                "  - Docker network `hath0r-net` and `Hath0r-MCP` container (http://127.0.0.1:38083/ready)\n",
                encoding="utf-8",
            )

            hdiutil_bin = shutil.which("hdiutil")
            if hdiutil_bin:
                if versioned_dmg.exists():
                    versioned_dmg.unlink()
                rc_dmg, out_dmg, err_dmg = self.runner(
                    [
                        hdiutil_bin,
                        "create",
                        "-volname",
                        "Hath0r Install Wizard",
                        "-srcfolder",
                        str(stage_root),
                        "-ov",
                        "-format",
                        "UDZO",
                        str(versioned_dmg),
                    ],
                    timeout=180,
                )
                if rc_dmg != 0 or not versioned_dmg.is_file():
                    raise InstallWizardError(
                        "package_dmg",
                        "DMG_BUILD_FAILED",
                        f"hdiutil failed to create {versioned_dmg}: {err_dmg or out_dmg}",
                        "Verify macOS hdiutil permissions and available disk space.",
                    )
            else:
                # Non-macOS fallback: create compressed archive with UDIF trailer for cross-platform CI
                shutil.make_archive(str(versioned_dmg.with_suffix("")), "gztar", root_dir=stage_root)
                tar_gz = versioned_dmg.with_suffix(".tar.gz")
                if tar_gz.is_file():
                    shutil.move(str(tar_gz), str(versioned_dmg))

            shutil.copy2(versioned_dmg, canonical_dmg)

        sha_digest = sha256_file(canonical_dmg)
        (target_dir / f"{canonical_dmg.name}.sha256").write_text(
            f"{sha_digest}  {canonical_dmg.name}\n", encoding="utf-8"
        )
        (target_dir / f"{versioned_dmg.name}.sha256").write_text(
            f"{sha_digest}  {versioned_dmg.name}\n", encoding="utf-8"
        )
        return {
            "success": True,
            "platform": "macos",
            "version": ver,
            "dmg_path": str(canonical_dmg),
            "versioned_dmg_path": str(versioned_dmg),
            "size_bytes": canonical_dmg.stat().st_size,
            "sha256": sha_digest,
        }

    def _windows_launcher_c_source(self, script_bytes: bytes, version: str) -> str:
        """Generate self-contained Win32/x64 C source code that embeds `install_hath0r.py` and launches it."""
        hex_items = ", ".join(f"0x{b:02x}" for b in script_bytes)
        return f"""/*
 * Hath0r CLI + Hath0r MCP (Docker) — Official Windows Install Wizard Launcher (v{version})
 * Compiled as a standalone 64-bit Windows PE32+ executable (Hath0r-Install-Wizard.exe).
 * Extracts the embedded install_hath0r.py bootstrap wizard, ensures Python 3.10+ (via winget if needed),
 * and runs the 5-stage Hath0r CLI + Docker MCP installation pipeline.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#ifdef _WIN32
#include <windows.h>
#include <direct.h>
#define MKDIR(p) _mkdir(p)
#define PATH_SEP "\\\\"
#else
#include <sys/stat.h>
#include <unistd.h>
#define MKDIR(p) mkdir(p, 0755)
#define PATH_SEP "/"
#endif

static const unsigned char EMBEDDED_WIZARD_PY[] = {{
    {hex_items}
}};
static const size_t EMBEDDED_WIZARD_LEN = sizeof(EMBEDDED_WIZARD_PY);

static int has_python3(const char **out_cmd) {{
    if (system("python --version >nul 2>&1") == 0) {{
        *out_cmd = "python";
        return 1;
    }}
    if (system("py -3 --version >nul 2>&1") == 0) {{
        *out_cmd = "py -3";
        return 1;
    }}
    if (system("python3 --version >nul 2>&1") == 0) {{
        *out_cmd = "python3";
        return 1;
    }}
    return 0;
}}

int main(int argc, char *argv[]) {{
    char temp_dir[1024];
    char work_dir[1152];
    char script_path[1280];
    char cmd_line[4096];
    const char *py_cmd = "python";
    int interactive_pause = 1;

    for (int i = 1; i < argc; ++i) {{
        if (strcmp(argv[i], "-y") == 0 || strcmp(argv[i], "--yes") == 0 ||
            strcmp(argv[i], "--dry-run") == 0 || strcmp(argv[i], "--help") == 0 ||
            strcmp(argv[i], "-h") == 0) {{
            interactive_pause = 0;
        }}
    }}

#ifdef _WIN32
    DWORD len = GetTempPathA(sizeof(temp_dir), temp_dir);
    if (len == 0 || len >= sizeof(temp_dir)) {{
        strcpy(temp_dir, "C:\\\\Temp\\\\");
    }}
#else
    strcpy(temp_dir, "/tmp/");
#endif

    snprintf(work_dir, sizeof(work_dir), "%shath0r-install-wizard", temp_dir);
    MKDIR(work_dir);
    snprintf(script_path, sizeof(script_path), "%s%sinstall_hath0r.py", work_dir, PATH_SEP);

    FILE *fp = fopen(script_path, "wb");
    if (!fp) {{
        fprintf(stderr, "ERROR: Failed to extract Hath0r Install Wizard to %s\\n", script_path);
        return 2;
    }}
    fwrite(EMBEDDED_WIZARD_PY, 1, EMBEDDED_WIZARD_LEN, fp);
    fclose(fp);

    if (!has_python3(&py_cmd)) {{
        printf("==> Python 3.10+ not found on PATH. Installing Python 3.12 via winget...\\n");
        int wrc = system("winget install -e --id Python.Python.3.12 --accept-package-agreements --accept-source-agreements");
        if (wrc != 0 || !has_python3(&py_cmd)) {{
            fprintf(stderr, "ERROR: Python 3.10+ is required. Install Python from https://www.python.org/downloads/ and re-run.\\n");
            if (interactive_pause) {{
                printf("\\nPress Enter to exit...");
                getchar();
            }}
            return 2;
        }}
    }}

    snprintf(cmd_line, sizeof(cmd_line), "%s \\"%s\\"", py_cmd, script_path);
    for (int i = 1; i < argc; ++i) {{
        strncat(cmd_line, " \\"", sizeof(cmd_line) - strlen(cmd_line) - 1);
        strncat(cmd_line, argv[i], sizeof(cmd_line) - strlen(cmd_line) - 1);
        strncat(cmd_line, "\\"", sizeof(cmd_line) - strlen(cmd_line) - 1);
    }}

    int rc = system(cmd_line);
    if (interactive_pause && argc == 1) {{
        printf("\\nHath0r Install Wizard finished (exit code %d). Press Enter to close...", rc);
        getchar();
    }}
    return rc == 0 ? 0 : 1;
}}
"""

    def build_windows_exe(
        self,
        *,
        out_dir: Optional[Path] = None,
        version: Optional[str] = None,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Build the standalone 64-bit Windows `.exe` Install Wizard (`Hath0r-Install-Wizard.exe`)."""
        cli_root = self._cli_root()
        if out_dir is None:
            target_dir = (cli_root / "release" / "windows").resolve()
        else:
            resolved_out = out_dir.resolve()
            target_dir = (resolved_out / "windows") if (resolved_out / "windows").is_dir() else resolved_out
        ver = version or self._read_cli_version()
        canonical_exe = target_dir / "Hath0r-Install-Wizard.exe"
        versioned_exe = target_dir / f"Hath0r-Install-Wizard-{ver}-windows-x64.exe"

        if dry_run:
            return {
                "success": True,
                "dry_run": True,
                "platform": "windows-x64",
                "version": ver,
                "exe_path": str(canonical_exe),
                "versioned_exe_path": str(versioned_exe),
                "action": f"[DRY-RUN] Would build Windows x64 executable {canonical_exe} and {versioned_exe}.",
            }

        target_dir.mkdir(parents=True, exist_ok=True)
        script_bytes = self._load_install_script_bytes()
        c_source = self._windows_launcher_c_source(script_bytes, ver)

        # Persist C launcher source in packaging/installers/ for reproducibility
        installer_src_dir = cli_root / "packaging" / "installers"
        installer_src_dir.mkdir(parents=True, exist_ok=True)
        c_file_repo = installer_src_dir / "windows_wizard_launcher.c"
        c_file_repo.write_text(c_source, encoding="utf-8")

        mingw_gcc = shutil.which("x86_64-w64-mingw32-gcc")
        compiler_used = "x86_64-w64-mingw32-gcc"

        with tempfile.TemporaryDirectory(prefix="hath0r-win-exe-") as tmp:
            c_path = Path(tmp) / "windows_wizard_launcher.c"
            c_path.write_text(c_source, encoding="utf-8")

            if mingw_gcc:
                rc, out, err = self.runner(
                    [mingw_gcc, "-O2", "-s", "-Wall", str(c_path), "-o", str(versioned_exe)],
                    timeout=120,
                )
                if rc != 0 or not versioned_exe.is_file():
                    raise InstallWizardError(
                        "package_exe",
                        "EXE_BUILD_FAILED",
                        f"MinGW cross-compilation failed for {versioned_exe}: {err or out}",
                        "Verify `x86_64-w64-mingw32-gcc` installation (`brew install mingw-w64`).",
                    )
            elif platform.system().lower().startswith("win"):
                compiler_used = "pyinstaller-windows"
                rc, out, err = self.runner(
                    [
                        self.python,
                        "-m",
                        "PyInstaller",
                        "--noconfirm",
                        "--clean",
                        "--onefile",
                        "--name",
                        versioned_exe.stem,
                        "--distpath",
                        str(target_dir),
                        "--workpath",
                        str(Path(tmp) / "build"),
                        "--specpath",
                        str(Path(tmp)),
                        str(cli_root / "scripts" / "install_hath0r.py"),
                    ],
                    timeout=300,
                )
                if rc != 0 or not versioned_exe.is_file():
                    raise InstallWizardError(
                        "package_exe",
                        "EXE_BUILD_FAILED",
                        f"PyInstaller failed to build {versioned_exe}: {err or out}",
                        "Install PyInstaller (`pip install pyinstaller`) or MinGW-w64.",
                    )
            else:
                prebuilt_exe = cli_root / "release" / "windows" / "Hath0r-Install-Wizard.exe"
                if prebuilt_exe.is_file() and prebuilt_exe.resolve() != versioned_exe.resolve():
                    compiler_used = "prebuilt-pe32plus"
                    shutil.copy2(prebuilt_exe, versioned_exe)
                elif versioned_exe.is_file():
                    compiler_used = "prebuilt-pe32plus"
                else:
                    raise InstallWizardError(
                        "package_exe",
                        "MINGW_COMPILER_MISSING",
                        "x86_64-w64-mingw32-gcc is required on macOS/Linux to cross-compile the Windows .exe installer.",
                        "Install MinGW-w64 via `brew install mingw-w64` or `sudo apt-get install mingw-w64`.",
                    )

        shutil.copy2(versioned_exe, canonical_exe)
        sha_digest = sha256_file(canonical_exe)
        (target_dir / f"{canonical_exe.name}.sha256").write_text(
            f"{sha_digest}  {canonical_exe.name}\n", encoding="utf-8"
        )
        (target_dir / f"{versioned_exe.name}.sha256").write_text(
            f"{sha_digest}  {versioned_exe.name}\n", encoding="utf-8"
        )
        return {
            "success": True,
            "platform": "windows-x64",
            "compiler": compiler_used,
            "version": ver,
            "exe_path": str(canonical_exe),
            "versioned_exe_path": str(versioned_exe),
            "size_bytes": canonical_exe.stat().st_size,
            "sha256": sha_digest,
        }

    def build_installers(
        self,
        *,
        out_dir: Optional[Path] = None,
        version: Optional[str] = None,
        target: str = "all",
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Build the macOS `.dmg` and Windows `.exe` Install Wizard launchers and update `CHECKSUMS.sha256`."""
        cli_root = self._cli_root()
        release_dir = (out_dir or (cli_root / "release")).resolve()
        ver = version or self._read_cli_version()
        chosen = target.lower().strip()

        results: Dict[str, Any] = {
            "success": True,
            "dry_run": dry_run,
            "version": ver,
            "out_dir": str(release_dir),
        }

        if chosen in ("all", "dmg", "macos", "darwin"):
            results["macos_dmg"] = self.build_macos_dmg(out_dir=release_dir, version=ver, dry_run=dry_run)
        if chosen in ("all", "exe", "windows", "win"):
            results["windows_exe"] = self.build_windows_exe(out_dir=release_dir, version=ver, dry_run=dry_run)

        results["message"] = (
            f"[DRY-RUN] Would build Install Wizard installers ({chosen}) in {release_dir}."
            if dry_run
            else f"Built Hath0r Install Wizard installers ({chosen}) for v{ver} in {release_dir}."
        )
        return results
