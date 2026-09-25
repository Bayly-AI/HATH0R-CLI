"""Repository hygiene and organization micro-bots for repo-clean-factory.

Includes:
- RepoHygieneBot: Scans root directory for errant or unwhitelisted files.
- ConfigOrganizerBot: Relocates or validates configuration files in .cfg/ or cfg/.
- KnowledgeOrganizerBot: Verifies knowledge, agent rules, and docs are partitioned into topic directories.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Set

# Whitelist of allowable project root files per UPL and standard toolchain
ALLOWED_ROOT_FILES: Set[str] = {
    # Core Hath0r / UPL files
    "AGENTS.md",
    "WARP.md",
    "README.md",
    "LICENSE",
    "NOTICE",
    "MANIFEST.json",
    "VERSION",
    "CHANGELOG.md",
    "Makefile",
    # Toolchain configs required at root by external tools (or until moved)
    "pyproject.toml",
    "pytest.ini",
    "sonar-project.properties",
    ".gitignore",
    ".gitmodules",
    ".dockerignore",
    ".editorconfig",
    ".env.example",
    # Containers & Dependencies
    "Dockerfile",
    "Containerfile",
    "requirements.txt",
    "requirements-dev.txt",
    "docker-compose.yml",
    # Frontend / JS / TS ecosystem
    "package.json",
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "tsconfig.json",
    "tsconfig.app.json",
    "tsconfig.node.json",
    "tsconfig.server.json",
    "vite.config.ts",
    "vitest.config.ts",
    "vitest.smoke.config.ts",
    "playwright.config.ts",
    "eslint.config.js",
    ".prettierrc.json",
    ".prettierignore",
    "index.html",
    "nginx.conf",
    # Coverage outputs
    ".coverage",
    "coverage.xml",
    # OS files
    ".DS_Store",
}

# Directories canonically allowed at root
ALLOWED_ROOT_DIRS: Set[str] = {
    ".git",
    ".github",
    ".hath0r",
    ".cfg",
    "cfg",
    "contracts",
    "docs",
    "src",
    "tests",
    "test",
    "lib",
    "bin",
    "scripts",
    "packaging",
    "dist",
    "data",
    "logs",
    "reports",
    "knowledgebase",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".coverage",
}

# Config extensions subject to organization
CONFIG_EXTENSIONS: Set[str] = {".yaml", ".yml", ".json", ".toml", ".ini", ".conf", ".xml"}

# Root configs that are permitted to remain at root if required by tools
ROOT_ESSENTIAL_CONFIGS: Set[str] = {
    "pyproject.toml",
    "pytest.ini",
    "sonar-project.properties",
    "MANIFEST.json",
    "package.json",
    "package-lock.json",
    "tsconfig.json",
    "tsconfig.app.json",
    "tsconfig.node.json",
    "tsconfig.server.json",
    "docker-compose.yml",
    ".prettierrc.json",
    "nginx.conf",
    "coverage.xml",
}

# Maximum line count for a markdown file before flagging as potentially monolithic
MAX_MONOLITHIC_LINES: int = 400


@dataclass
class RepoHygieneBot:
    """Audits root directory against allowable files and identifies errant files."""

    cwd: Path = field(default_factory=Path.cwd)

    def scan_root(self) -> Dict[str, Any]:
        """Scan project root for unapproved or errant files."""
        errant_files: List[Dict[str, Any]] = []
        root_files: List[str] = []

        for p in self.cwd.iterdir():
            name = p.name
            if p.is_file():
                root_files.append(name)
                if name not in ALLOWED_ROOT_FILES:
                    errant_files.append({
                        "name": name,
                        "path": str(p),
                        "size_bytes": p.stat().st_size,
                        "is_config": p.suffix.lower() in CONFIG_EXTENSIONS,
                    })

        return {
            "success": True,
            "total_root_files": len(root_files),
            "errant_count": len(errant_files),
            "errant_files": errant_files,
            "clean": len(errant_files) == 0,
        }

    def clean_root(self, dry_run: bool = False, archive_dir: str = ".hath0r/spool/archive") -> Dict[str, Any]:
        """Move errant non-config files to archive spool or report action."""
        scan = self.scan_root()
        errant = scan.get("errant_files", [])
        actions: List[Dict[str, Any]] = []

        target_archive = self.cwd / archive_dir

        for item in errant:
            p = Path(item["path"])
            # If it's a config file, let ConfigOrganizerBot handle it
            if item.get("is_config"):
                continue

            dest = target_archive / p.name
            action_desc = (
                f"[DRY-RUN] Would move {p.name} -> {archive_dir}/"
                if dry_run
                else f"Moved {p.name} -> {archive_dir}/"
            )
            if not dry_run:
                target_archive.mkdir(parents=True, exist_ok=True)
                shutil.move(str(p), str(dest))

            actions.append({
                "file": p.name,
                "action": action_desc,
                "destination": str(dest),
                "moved": not dry_run,
            })

        return {
            "success": True,
            "dry_run": dry_run,
            "actions": actions,
            "cleaned_count": len(actions),
        }


@dataclass
class ConfigOrganizerBot:
    """Manages placement of configuration files, moving non-root configs to .cfg/ or cfg/."""

    cwd: Path = field(default_factory=Path.cwd)

    def scan_misplaced_configs(self) -> Dict[str, Any]:
        """Identify configuration files situated in project root that belong in .cfg/ or cfg/."""
        misplaced: List[Dict[str, Any]] = []
        for p in self.cwd.iterdir():
            if p.is_file():
                name = p.name
                if p.suffix.lower() in CONFIG_EXTENSIONS:
                    if name not in ROOT_ESSENTIAL_CONFIGS and name not in ALLOWED_ROOT_FILES:
                        misplaced.append({
                            "name": name,
                            "path": str(p),
                            "recommended_dest": ".cfg/" + name,
                        })

        return {
            "success": True,
            "misplaced_count": len(misplaced),
            "misplaced_configs": misplaced,
            "clean": len(misplaced) == 0,
        }

    def organize_configs(self, target_folder: str = ".cfg", dry_run: bool = False) -> Dict[str, Any]:
        """Relocate non-essential root config files into target folder (default: .cfg)."""
        scan = self.scan_misplaced_configs()
        misplaced = scan.get("misplaced_configs", [])
        dest_dir = self.cwd / target_folder
        relocations: List[Dict[str, Any]] = []

        for item in misplaced:
            src = Path(item["path"])
            dest = dest_dir / src.name
            action_desc = (
                f"[DRY-RUN] Would relocate {src.name} -> {target_folder}/"
                if dry_run
                else f"Relocated {src.name} -> {target_folder}/"
            )
            if not dry_run:
                dest_dir.mkdir(parents=True, exist_ok=True)
                shutil.move(str(src), str(dest))

            relocations.append({
                "file": src.name,
                "source": str(src),
                "destination": str(dest),
                "action": action_desc,
                "moved": not dry_run,
            })

        return {
            "success": True,
            "dry_run": dry_run,
            "target_folder": target_folder,
            "relocations": relocations,
            "count": len(relocations),
        }


@dataclass
class KnowledgeOrganizerBot:
    """Verifies that knowledge, agent rules, and docs are partitioned into organized topic folders."""

    cwd: Path = field(default_factory=Path.cwd)

    def audit_knowledge_structure(self) -> Dict[str, Any]:
        """Audit docs/ and .hath0r/knowledgebase/ for structure and monolithic files."""
        findings: List[Dict[str, Any]] = []
        scanned_files = 0

        target_paths = [
            self.cwd / "docs",
            self.cwd / ".hath0r" / "knowledgebase",
            self.cwd / "rules",
        ]

        for base in target_paths:
            if not base.is_dir():
                continue

            # Check root of documentation / knowledge directory for stray non-index markdown
            for item in base.iterdir():
                if item.is_file() and item.suffix.lower() == ".md":
                    # Single top-level files (apart from README, INDEX, WARP, AGENTS)
                    if item.name.upper() not in {"README.MD", "INDEX.MD", "WARP.MD", "AGENTS.MD", "LLMS.TXT"}:
                        line_count = len(item.read_text(encoding="utf-8", errors="ignore").splitlines())
                        scanned_files += 1
                        if line_count > MAX_MONOLITHIC_LINES:
                            findings.append({
                                "file": str(item.relative_to(self.cwd)),
                                "lines": line_count,
                                "issue": "monolithic_file",
                                "recommendation": (
                                    f"Partition into modular files inside a dedicated subdirectory ({item.stem}/)"
                                ),
                            })

            # Check all md files recursively for monolithic files
            for md in base.rglob("*.md"):
                scanned_files += 1
                try:
                    lines = len(md.read_text(encoding="utf-8", errors="ignore").splitlines())
                    if lines > MAX_MONOLITHIC_LINES and md.name.upper() not in {"INDEX.MD", "INDEX.JSON"}:
                        rel = str(md.relative_to(self.cwd))
                        # Avoid duplicates
                        if not any(f["file"] == rel for f in findings):
                            findings.append({
                                "file": rel,
                                "lines": lines,
                                "issue": "oversized_monolithic_knowledge",
                                "recommendation": "Split content across topic-based subfolder documents",
                            })
                except Exception:
                    pass

        return {
            "success": True,
            "scanned_count": scanned_files,
            "findings_count": len(findings),
            "findings": findings,
            "organized": len(findings) == 0,
        }
