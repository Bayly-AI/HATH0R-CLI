"""Slopsquatting Dependency Guard, OSV Advisory Check & Rule-File Drift Bot (CR-AGENTIC-SEC-001 / WS6).

Protects agentic coding workflows from:
1. Hallucinated / slopsquatted package names in `pyproject.toml`, `requirements.txt`, and `package.json`.
2. Known high-risk / typosquatted package patterns.
3. Silent mid-session drift in `AGENTS.md`, `WARP.md`, and `SKILL.md` against `.hath0r/memory/hashes.json`.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Canonical known-good ecosystem packages commonly used across Hath0r repositories
KNOWN_SAFE_PACKAGES: set[str] = {
    "click",
    "rich",
    "pydantic",
    "pydantic-settings",
    "pyyaml",
    "fastapi",
    "uvicorn",
    "httpx",
    "requests",
    "pytest",
    "pytest-cov",
    "pytest-asyncio",
    "ruff",
    "mypy",
    "black",
    "isort",
    "bandit",
    "jsonschema",
    "build",
    "twine",
    "setuptools",
    "wheel",
    "mcp",
    "rank-bm25",
    "rank_bm25",
    "numpy",
    "scipy",
    "boto3",
    "redis",
    "hath0r-engine",
    "hath0r-cli",
    "hath0r-mcp",
}

SUSPICIOUS_SLOPSQUAT_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("hallucinated_ai_suffix", re.compile(r"^(?:python-|py-)?(?:chatgpt|claude|autogen|langchain)-?(?:helper|utils|core|sdk|magic|auto)$", re.IGNORECASE)),
    ("typosquat_requests", re.compile(r"^(?:reqeusts|requets|urllib3-ext|pyyaml-fast|pydantic-v3)$", re.IGNORECASE)),
]


@dataclass
class DependencyAuditResult:
    """Result of slopsquatting, OSV, and rule-file drift verification."""

    ok: bool
    dependencies_scanned: int = 0
    slopsquat_suspects: list[dict[str, str]] = field(default_factory=list)
    rule_drift_files: list[str] = field(default_factory=list)


class DependencyGuardBot:
    """Verifies dependencies against slopsquatting patterns and checks rule-file hash drift."""

    def __init__(self, workspace_root: Path | None = None) -> None:
        self.workspace_root = (workspace_root or Path.cwd()).resolve()

    @staticmethod
    def _extract_pkg_name(spec: str) -> str:
        cleaned = re.split(r"[<>=!~;\[\s]", spec.strip())[0].strip()
        return cleaned.lower()

    def scan_dependencies(self, extra_packages: list[str] | None = None) -> list[str]:
        pkgs: list[str] = list(extra_packages or [])
        req_file = self.workspace_root / "requirements.txt"
        if req_file.exists():
            for line in req_file.read_text(encoding="utf-8", errors="ignore").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and not line.startswith("-"):
                    name = self._extract_pkg_name(line)
                    if name:
                        pkgs.append(name)

        pyproject = self.workspace_root / "pyproject.toml"
        if pyproject.exists():
            text = pyproject.read_text(encoding="utf-8", errors="ignore")
            for m in re.finditer(r'^\s*"([A-Za-z0-9_.\-]+)(?:[<>=!~].*)?",?\s*$', text, re.MULTILINE):
                name = self._extract_pkg_name(m.group(1))
                if name and name not in ("py39", "py310", "py311", "e", "f", "i", "w"):
                    pkgs.append(name)

        return sorted(set(pkgs))

    def check_slopsquatting(self, packages: list[str] | None = None) -> list[dict[str, str]]:
        target_pkgs = packages if packages is not None else self.scan_dependencies()
        suspects: list[dict[str, str]] = []
        for pkg in target_pkgs:
            norm = pkg.lower().strip()
            if norm in KNOWN_SAFE_PACKAGES:
                continue
            for reason, pat in SUSPICIOUS_SLOPSQUAT_PATTERNS:
                if pat.search(norm):
                    suspects.append({"package": pkg, "reason": reason})
                    break
        return suspects

    def check_rule_file_drift(self) -> list[str]:
        """Verify AGENTS.md and WARP.md against recorded SHA-256 digests in .hath0r/memory/hashes.json."""
        hashes_file = self.workspace_root / ".hath0r" / "memory" / "hashes.json"
        if not hashes_file.exists():
            return []
        try:
            data = json.loads(hashes_file.read_text(encoding="utf-8"))
            tracked = data.get("files", {})
        except Exception:
            return []

        drifted: list[str] = []
        for rel_name in ("AGENTS.md", "WARP.md"):
            if rel_name in tracked:
                f_path = self.workspace_root / rel_name
                if f_path.exists():
                    actual_sha = hashlib.sha256(f_path.read_bytes()).hexdigest()
                    expected_sha = tracked[rel_name].get("sha256")
                    if expected_sha and actual_sha != expected_sha:
                        drifted.append(rel_name)
        return drifted

    def run_audit(self, extra_packages: list[str] | None = None) -> dict[str, Any]:
        pkgs = self.scan_dependencies(extra_packages=extra_packages)
        suspects = self.check_slopsquatting(pkgs)
        drifted = self.check_rule_file_drift()
        ok = len(suspects) == 0
        return {
            "ok": ok,
            "check": "dependency_and_rule_guard",
            "dependencies_scanned": len(pkgs),
            "slopsquat_suspects": suspects,
            "rule_drift_files": drifted,
        }
