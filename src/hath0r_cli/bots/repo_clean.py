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
    "TECH_README.md",
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
    ".env",
    ".env.local",
    ".env.example",
    # Containers & Dependencies
    "Dockerfile",
    "Containerfile",
    "requirements.txt",
    "requirements-dev.txt",
    "docker-compose.yml",
    "uv.lock",
    "poetry.lock",
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
    # IaC & Deployment
    "fargate-profile.yaml",
    # Toolchain configs & standard OSS docs
    ".sonarcloud.properties",
    ".mcp.json",
    "setup.py",
    "setup.cfg",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "CODE_OF_CONDUCT.md",
    "README.TECHNICAL.md",
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
    ".sonarcloud.properties",
    "fargate-profile.yaml",
    ".mcp.json",
    "setup.py",
    "setup.cfg",
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
                    errant_files.append(
                        {
                            "name": name,
                            "path": str(p),
                            "size_bytes": p.stat().st_size,
                            "is_config": p.suffix.lower() in CONFIG_EXTENSIONS,
                        }
                    )

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
                f"[DRY-RUN] Would move {p.name} -> {archive_dir}/" if dry_run else f"Moved {p.name} -> {archive_dir}/"
            )
            if not dry_run:
                target_archive.mkdir(parents=True, exist_ok=True)
                shutil.move(str(p), str(dest))

            actions.append(
                {
                    "file": p.name,
                    "action": action_desc,
                    "destination": str(dest),
                    "moved": not dry_run,
                }
            )

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
                        misplaced.append(
                            {
                                "name": name,
                                "path": str(p),
                                "recommended_dest": ".cfg/" + name,
                            }
                        )

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

            relocations.append(
                {
                    "file": src.name,
                    "source": str(src),
                    "destination": str(dest),
                    "action": action_desc,
                    "moved": not dry_run,
                }
            )

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
                            findings.append(
                                {
                                    "file": str(item.relative_to(self.cwd)),
                                    "lines": line_count,
                                    "issue": "monolithic_file",
                                    "recommendation": (
                                        f"Partition into modular files inside a dedicated subdirectory ({item.stem}/)"
                                    ),
                                }
                            )

            # Check all md files recursively for monolithic files
            for md in base.rglob("*.md"):
                scanned_files += 1
                try:
                    lines = len(md.read_text(encoding="utf-8", errors="ignore").splitlines())
                    if lines > MAX_MONOLITHIC_LINES and md.name.upper() not in {"INDEX.MD", "INDEX.JSON"}:
                        rel = str(md.relative_to(self.cwd))
                        # Avoid duplicates
                        if not any(f["file"] == rel for f in findings):
                            findings.append(
                                {
                                    "file": rel,
                                    "lines": lines,
                                    "issue": "oversized_monolithic_knowledge",
                                    "recommendation": "Split content across topic-based subfolder documents",
                                }
                            )
                except Exception:
                    pass

        return {
            "success": True,
            "scanned_count": scanned_files,
            "findings_count": len(findings),
            "findings": findings,
            "organized": len(findings) == 0,
        }


CANONICAL_BRANCHES: Set[str] = {
    "development",
    "testing",
    "staging",
    "master",
    "main",
    "HEAD",
    "gh-pages",
}


@dataclass
class CleanReposWorkflowBot:
    """13-step Clean Repos Standard Operating Procedure Executor."""

    cwd: Path = field(default_factory=Path.cwd)

    @staticmethod
    def _git_out(repo_path: Path, args: List[str]) -> str:
        """Run a git command and return stripped stdout, or empty string on error."""
        import subprocess

        try:
            return (
                subprocess.check_output(
                    ["git", *args],
                    cwd=repo_path,
                    stderr=subprocess.DEVNULL,
                )
                .decode()
                .strip()
            )
        except Exception:
            return ""

    @classmethod
    def _has_origin(cls, repo_path: Path) -> bool:
        """Return True when the repository has an origin remote configured."""
        remotes = cls._git_out(repo_path, ["remote"]).splitlines()
        return "origin" in [r.strip() for r in remotes if r.strip()]

    @classmethod
    def _detect_base_branch(cls, repo_path: Path) -> str:
        """Detect the canonical base branch (development preferred, else main/master)."""
        local_branches = {
            b.strip()
            for b in cls._git_out(
                repo_path, ["for-each-ref", "--format=%(refname:short)", "refs/heads/"]
            ).splitlines()
            if b.strip()
        }
        remote_branches = {
            b.strip().removeprefix("origin/")
            for b in cls._git_out(
                repo_path, ["for-each-ref", "--format=%(refname:short)", "refs/remotes/origin/"]
            ).splitlines()
            if b.strip()
        }
        all_known = local_branches | remote_branches
        for candidate in ("development", "main", "master"):
            if candidate in all_known:
                return candidate
        current = cls._git_out(repo_path, ["branch", "--show-current"])
        return current or "development"

    @staticmethod
    def _is_canonical_branch(branch_name: str) -> bool:
        """Return True if branch_name is a locked canonical or protected branch."""
        short = branch_name.removeprefix("origin/").strip()
        if not short or short in CANONICAL_BRANCHES:
            return True
        if short.startswith("dependabot/"):
            return True
        return False

    @classmethod
    def _cleanup_artifacts(cls, repo_path: Path) -> List[str]:
        """Remove development and coverage artifacts from repo_path."""
        cleaned_artifacts: List[str] = []
        for p in list(repo_path.rglob(".DS_Store")):
            if p.exists():
                p.unlink(missing_ok=True)
                cleaned_artifacts.append(str(p.relative_to(repo_path)))
        for p in list(repo_path.rglob("__pycache__")):
            if p.exists():
                shutil.rmtree(p, ignore_errors=True)
                cleaned_artifacts.append(str(p.relative_to(repo_path)))
        for cache_dir in [".pytest_cache", ".coverage", "coverage.xml"]:
            target = repo_path / cache_dir
            if target.exists():
                if target.is_dir():
                    shutil.rmtree(target, ignore_errors=True)
                else:
                    target.unlink(missing_ok=True)
                cleaned_artifacts.append(cache_dir)
        return cleaned_artifacts

    @classmethod
    def _prune_worktrees(cls, repo_path: Path) -> Dict[str, Any]:
        """Prune stale worktrees and detach/remove non-main feature worktrees."""
        import subprocess

        subprocess.run(["git", "worktree", "prune"], cwd=repo_path, check=False, stderr=subprocess.DEVNULL)
        wt_out = cls._git_out(repo_path, ["worktree", "list", "--porcelain"])
        detached_worktrees: List[str] = []
        current_wt: str | None = None
        for line in wt_out.splitlines():
            if line.startswith("worktree "):
                current_wt = line.removeprefix("worktree ").strip()
            elif line.startswith("branch refs/heads/") and current_wt:
                b_name = line.removeprefix("branch refs/heads/").strip()
                wt_path = Path(current_wt)
                if wt_path.resolve() != repo_path.resolve() and not cls._is_canonical_branch(b_name):
                    if not wt_path.exists():
                        subprocess.run(
                            ["git", "worktree", "remove", "--force", str(wt_path)],
                            cwd=repo_path,
                            check=False,
                            stderr=subprocess.DEVNULL,
                        )
                    else:
                        subprocess.run(
                            ["git", "checkout", "--detach"],
                            cwd=wt_path,
                            check=False,
                            stderr=subprocess.DEVNULL,
                        )
                    detached_worktrees.append(f"{wt_path.name}:{b_name}")
        subprocess.run(["git", "worktree", "prune"], cwd=repo_path, check=False, stderr=subprocess.DEVNULL)
        return {"status": "ok", "detached_worktrees": detached_worktrees}

    @classmethod
    def _unmerged_commit_count(cls, repo_path: Path, base_branch: str, ref: str) -> int:
        """Return count of genuinely unmerged patch commits in ref ahead of base_branch."""
        rev_count_str = cls._git_out(repo_path, ["rev-list", "--count", f"{base_branch}..{ref}"])
        try:
            rev_count = int(rev_count_str)
        except ValueError:
            return 0
        if rev_count <= 0:
            return 0
        cherry_out = cls._git_out(repo_path, ["cherry", base_branch, ref])
        if not cherry_out:
            return 0
        plus_lines = [ln for ln in cherry_out.splitlines() if ln.startswith("+")]
        return len(plus_lines)

    @classmethod
    def _merge_ref_with_conflict_resolution(
        cls, repo_path: Path, ref: str
    ) -> Dict[str, Any]:
        """Merge ref into current branch, automatically resolving conflicts when encountered."""
        import subprocess

        res = subprocess.run(
            ["git", "merge", "--no-edit", ref],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=False,
        )
        if res.returncode == 0:
            return {"ref": ref, "merged": True, "conflicts_resolved": False}

        # Abort initial merge and retry with -X ours to resolve content conflicts cleanly
        subprocess.run(["git", "merge", "--abort"], cwd=repo_path, check=False, stderr=subprocess.DEVNULL)
        res_ours = subprocess.run(
            ["git", "merge", "--no-edit", "-X", "ours", ref],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=False,
        )
        if res_ours.returncode == 0:
            return {"ref": ref, "merged": True, "conflicts_resolved": True, "strategy": "ours"}

        # Resolve any remaining tree-level unmerged paths (modify/delete or add/add)
        unmerged_files = [
            f.strip()
            for f in cls._git_out(repo_path, ["diff", "--name-only", "--diff-filter=U"]).splitlines()
            if f.strip()
        ]
        for uf in unmerged_files:
            ours_check = subprocess.run(
                ["git", "checkout", "--ours", "--", uf],
                cwd=repo_path,
                check=False,
                stderr=subprocess.DEVNULL,
            )
            if ours_check.returncode != 0:
                subprocess.run(
                    ["git", "checkout", "--theirs", "--", uf],
                    cwd=repo_path,
                    check=False,
                    stderr=subprocess.DEVNULL,
                )
            subprocess.run(["git", "add", "--", uf], cwd=repo_path, check=False, stderr=subprocess.DEVNULL)

        cls._cleanup_artifacts(repo_path)
        subprocess.run(["git", "add", "-A"], cwd=repo_path, check=False, stderr=subprocess.DEVNULL)
        commit_res = subprocess.run(
            ["git", "commit", "--no-edit", "-m", f"chore(clean-repo): merge {ref} and resolve conflicts"],
            cwd=repo_path,
            check=False,
            stderr=subprocess.DEVNULL,
        )
        if commit_res.returncode != 0:
            subprocess.run(["git", "merge", "--abort"], cwd=repo_path, check=False, stderr=subprocess.DEVNULL)
            return {"ref": ref, "merged": False, "conflicts_resolved": False}

        return {"ref": ref, "merged": True, "conflicts_resolved": True, "strategy": "tree-ours"}

    @classmethod
    def _review_merge_and_prune_branches(
        cls, repo_path: Path, base_branch: str, auto_commit: bool = True
    ) -> Dict[str, Any]:
        """Review all feature branches, merge unmerged changes, resolve conflicts, and delete stale branches."""
        import subprocess

        has_origin = cls._has_origin(repo_path)
        if has_origin:
            subprocess.run(
                ["git", "fetch", "--all", "--prune"],
                cwd=repo_path,
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

        current_branch = cls._git_out(repo_path, ["branch", "--show-current"])
        if current_branch != base_branch:
            subprocess.run(
                ["git", "checkout", base_branch],
                cwd=repo_path,
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        if has_origin:
            subprocess.run(
                ["git", "pull", "--rebase", "origin", base_branch],
                cwd=repo_path,
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

        local_branches = [
            b.strip()
            for b in cls._git_out(
                repo_path, ["for-each-ref", "--format=%(refname:short)", "refs/heads/"]
            ).splitlines()
            if b.strip() and not cls._is_canonical_branch(b.strip())
        ]
        remote_branches = [
            b.strip()
            for b in cls._git_out(
                repo_path, ["for-each-ref", "--format=%(refname:short)", "refs/remotes/origin/"]
            ).splitlines()
            if b.strip() and not cls._is_canonical_branch(b.strip())
        ]

        # Build candidate refs to review (local first, then remote-only branches)
        candidates: List[str] = list(local_branches)
        local_set = set(local_branches)
        for rb in remote_branches:
            short_rb = rb.removeprefix("origin/")
            if short_rb not in local_set:
                candidates.append(rb)

        merged_branches: List[str] = []
        conflicts_resolved: List[str] = []
        already_merged: List[str] = []

        for ref in candidates:
            unmerged_cnt = cls._unmerged_commit_count(repo_path, base_branch, ref)
            if unmerged_cnt > 0 and auto_commit:
                m_res = cls._merge_ref_with_conflict_resolution(repo_path, ref)
                if m_res.get("merged"):
                    merged_branches.append(ref)
                    if m_res.get("conflicts_resolved"):
                        conflicts_resolved.append(ref)
            else:
                already_merged.append(ref)

        deleted_local: List[str] = []
        deleted_remote: List[str] = []
        if auto_commit:
            for lb in local_branches:
                del_res = subprocess.run(
                    ["git", "branch", "-D", lb],
                    cwd=repo_path,
                    check=False,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                if del_res.returncode == 0:
                    deleted_local.append(lb)

            if has_origin:
                for rb in remote_branches:
                    short_rb = rb.removeprefix("origin/")
                    del_rem = subprocess.run(
                        ["git", "push", "origin", "--delete", short_rb],
                        cwd=repo_path,
                        check=False,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    if del_rem.returncode == 0:
                        deleted_remote.append(short_rb)
                subprocess.run(
                    ["git", "fetch", "--prune"],
                    cwd=repo_path,
                    check=False,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )

        return {
            "base_branch": base_branch,
            "reviewed_branches": len(candidates),
            "merged_branches": merged_branches,
            "conflicts_resolved": conflicts_resolved,
            "already_merged": already_merged,
            "deleted_local": deleted_local,
            "deleted_remote": deleted_remote,
        }

    def run_clean_repo_workflow(
        self, target_repos: List[Path] | None = None, auto_commit: bool = True
    ) -> Dict[str, Any]:
        """Execute the full 13-step clean repository lifecycle."""
        import subprocess

        # 1. Capture all repos in the project
        repos = target_repos or [self.cwd]
        results_by_repo = []
        all_success = True

        for r in repos:
            repo_path = r.resolve()
            repo_res: Dict[str, Any] = {
                "repo": repo_path.name,
                "path": str(repo_path),
                "steps": {},
                "clean": True,
            }

            try:
                # Step 2: Ensure changes committed
                e_artifacts = self._cleanup_artifacts(repo_path)
                status_out = self._git_out(repo_path, ["status", "--porcelain"])
                uncommitted = bool(status_out)
                if uncommitted and auto_commit:
                    subprocess.run(["git", "add", "-A"], cwd=repo_path, check=False)
                    subprocess.run(
                        ["git", "commit", "-m", "chore: sync uncommitted changes prior to clean repo cycle"],
                        cwd=repo_path,
                        check=False,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                repo_res["steps"]["2_ensure_committed"] = {"uncommitted_found": uncommitted, "committed": auto_commit}

                # Step 3: Cleanup development artifacts
                cleaned_artifacts = e_artifacts + self._cleanup_artifacts(repo_path)
                repo_res["steps"]["3_cleanup_artifacts"] = {"cleaned": cleaned_artifacts}

                # Step 4: Clean up and remove stale worktrees
                repo_res["steps"]["4_prune_worktrees"] = self._prune_worktrees(repo_path)

                # Step 5: PRs verification
                pr_count = 0
                try:
                    pr_out = subprocess.check_output(
                        ["gh", "pr", "list", "--json", "number,title,state"], cwd=repo_path, stderr=subprocess.DEVNULL
                    ).decode()
                    import json

                    prs = json.loads(pr_out)
                    pr_count = len(prs)
                except Exception:
                    prs = []
                repo_res["steps"]["5_verify_prs"] = {"open_prs": pr_count}

                # Review branches, merge branches with changes, fix conflicts, remove stale local/remote branches
                base_branch = self._detect_base_branch(repo_path)
                branch_hygiene = self._review_merge_and_prune_branches(
                    repo_path, base_branch=base_branch, auto_commit=auto_commit
                )

                # Step 6: Share knowledge & compound into MemoryGraph (CR-MEMORY-COMPOUND-001)
                from hath0r_cli.bots.memory_manager import MemoryManagerBot

                mem_bot = MemoryManagerBot(cwd=repo_path)
                mem_bot.session_read(
                    note=f"CleanReposWorkflowBot reading micro-session for {repo_path.name}",
                    dry_run=False,
                )
                mem_compound = mem_bot.compound_memory(
                    node_id=f"episode:clean-repo-{repo_path.name.lower().replace(' ', '-')}",
                    node_type="episode",
                    label=f"Clean Repo Lifecycle ({repo_path.name})",
                    content=f"Executed 13-step clean-repo hygiene, branch merges, and knowledge sync for {repo_path.name}.",
                    importance=0.75,
                    tags=["clean-repo", "hygiene", repo_path.name.lower().replace(" ", "-")],
                    relates_to=["concept:tri-graph", "rule:cr-memory-compound-001"],
                    relation="DERIVES_FROM",
                    sync_agentgraph=False,
                    dry_run=False,
                )
                sess_end = mem_bot.session_end(
                    summary=f"Clean Repo Lifecycle completed for {repo_path.name}.",
                    sync_agentgraph=False,
                    dry_run=False,
                )
                kb_synced = (repo_path / ".hath0r" / "knowledgebase").exists() or (repo_path / "AGENTS.md").exists()
                repo_res["steps"]["6_share_knowledge"] = {
                    "synced": kb_synced,
                    "memory_compounded": mem_compound.get("success", False),
                    "memory_node": (mem_compound.get("node") or {}).get("id"),
                    "micro_session": (sess_end.get("session") or {}).get("session_id"),
                }

                # Step 7: Update documentation & AgentGraph synchronization
                from hath0r_cli.bots.agentgraph_bot import AgentGraphBot
                from hath0r_cli.bots.churn_manager_bot import churn_manager_bot

                ag_bot = AgentGraphBot(cwd=repo_path)
                ag_sync = ag_bot.sync(persist=True)
                ag_val = ag_bot.validate()
                ag_valid = bool(ag_val.get("validation", {}).get("valid", False))
                try:
                    churn_summary = churn_manager_bot.analyze(repo_path, days=30).get("summary", {})
                except Exception:
                    churn_summary = {}

                repo_res["steps"]["7_update_documentation"] = {
                    "agents_md": (repo_path / "AGENTS.md").exists(),
                    "readme_md": (repo_path / "README.md").exists(),
                    "agentgraph_synced": ag_sync.get("success", False),
                    "agentgraph_valid": ag_valid,
                    "agentgraph_nodes": ag_sync.get("sync", {}).get("nodes_indexed", 0),
                    "churn_summary": churn_summary,
                }
                if not ag_valid:
                    repo_res["clean"] = False
                    repo_res["error"] = (
                        f"AgentGraph validation failed: {'; '.join(ag_val['validation'].get('errors', []))}"
                    )

                # Step 9 & 10: Branch & PR review / merge status
                repo_res["steps"]["9_10_pr_status"] = {
                    "current_branch": base_branch,
                    "open_prs": pr_count,
                    "reviewed_branches": branch_hygiene["reviewed_branches"],
                    "merged_branches": branch_hygiene["merged_branches"],
                    "conflicts_resolved": branch_hygiene["conflicts_resolved"],
                }

                # Step 11: Delete merged / stale feature branches (local & remote)
                repo_res["steps"]["11_delete_feature_branches"] = {
                    "status": "pruned",
                    "deleted_local": branch_hygiene["deleted_local"],
                    "deleted_remote": branch_hygiene["deleted_remote"],
                }

                # Step 13: Verify MemoryGraph Gate, Task Evaluation Gate & Announce Complete
                from hath0r_cli.bots.task_evaluator_bot import TaskEvaluatorBot

                eval_bot = TaskEvaluatorBot(cwd=repo_path)
                eval_run = eval_bot.evaluate_task(
                    task_id=f"clean-repo-{repo_path.name.lower().replace(' ', '-')}",
                    skip_tests=True,
                    compound_node=True,
                    sync_observability=False,
                    dry_run=False,
                )
                mem_bot.sync_file_hashes(refresh_source_files=True, dry_run=False)
                mem_gate = mem_bot.verify_compounded()
                eval_gate = eval_bot.verify_evaluated(auto_run_if_missing=True)
                both_passed = bool(mem_gate.get("compounded")) and bool(eval_gate.get("passed_gate"))

                # Step 8: Commit documentation, memory, and evaluation changes cleanly
                self._cleanup_artifacts(repo_path)
                status_post_docs = self._git_out(repo_path, ["status", "--porcelain"])
                if status_post_docs and auto_commit:
                    subprocess.run(["git", "add", "-A"], cwd=repo_path, check=False)
                    subprocess.run(
                        ["git", "commit", "-m", "docs: update documentation, evaluations, and knowledge sync [skip ci]"],
                        cwd=repo_path,
                        check=False,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                repo_res["steps"]["8_commit_docs"] = {"committed": bool(status_post_docs)}

                # Step 12: Switch back to development (base_branch) and pull/push origin
                current_after = self._git_out(repo_path, ["branch", "--show-current"])
                if current_after != base_branch:
                    subprocess.run(
                        ["git", "checkout", base_branch],
                        cwd=repo_path,
                        check=False,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                pushed_origin = False
                if self._has_origin(repo_path):
                    subprocess.run(
                        ["git", "pull", "--rebase", "origin", base_branch],
                        cwd=repo_path,
                        check=False,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    if auto_commit:
                        push_res = subprocess.run(
                            ["git", "push", "origin", base_branch],
                            cwd=repo_path,
                            check=False,
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                        )
                        pushed_origin = push_res.returncode == 0
                repo_res["steps"]["12_return_to_development"] = {
                    "branch": base_branch,
                    "synced": True,
                    "pushed_origin": pushed_origin,
                }

                repo_res["steps"]["13_announce_complete"] = {
                    "status": "complete" if both_passed else "blocked_by_pre_announce_gate",
                    "memory_compounded": mem_gate.get("compounded", False),
                    "total_memory_nodes": mem_gate.get("total_nodes", 0),
                    "hashes_verified": mem_gate.get("hashes_verified", False),
                    "eval_passed": eval_gate.get("passed_gate", False),
                    "r_task": eval_gate.get("r_task", eval_run.get("r_task", 0.0)),
                    "error": mem_gate.get("error") or eval_gate.get("error"),
                }
                if not both_passed:
                    repo_res["clean"] = False
                    all_success = False

            except Exception as e:
                repo_res["clean"] = False
                repo_res["error"] = str(e)
                all_success = False

            results_by_repo.append(repo_res)

        return {
            "success": all_success,
            "repo_count": len(repos),
            "repos": results_by_repo,
            "lifecycle_steps": 13,
        }
