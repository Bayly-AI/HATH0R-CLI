"""Git Worktree Concurrency and Isolation Manager for Hath0r CLI."""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class WorktreeInfo:
    """Representation of an active git worktree."""

    path: str
    head_commit: str
    branch: str
    is_main: bool
    is_locked: bool = False
    lock_reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path,
            "head_commit": self.head_commit,
            "branch": self.branch,
            "is_main": self.is_main,
            "is_locked": self.is_locked,
            "lock_reason": self.lock_reason,
        }


class WorktreeManager:
    """Manages creation, inspection, and teardown of isolated git worktrees."""

    def __init__(self, repo_root: Optional[Path | str] = None) -> None:
        self.repo_root = Path(repo_root or os.getcwd()).resolve()

    def _find_git_root(self) -> Optional[Path]:
        """Locate root directory containing .git."""
        curr = self.repo_root
        while curr != curr.parent:
            if (curr / ".git").exists():
                return curr
            curr = curr.parent
        return None

    def list_worktrees(self) -> List[WorktreeInfo]:
        """Parse 'git worktree list --porcelain' into structured WorktreeInfo list."""
        git_root = self._find_git_root()
        if not git_root:
            return []

        try:
            res = subprocess.run(
                ["git", "worktree", "list", "--porcelain"],
                cwd=str(git_root),
                capture_output=True,
                text=True,
                check=True,
            )
            raw = res.stdout.strip()
            if not raw:
                return []

            worktrees: List[WorktreeInfo] = []
            entries = raw.split("\n\n")

            for entry in entries:
                lines = entry.strip().splitlines()
                wt_path = ""
                head = ""
                branch = ""
                is_locked = False
                lock_reason = ""

                for line in lines:
                    if line.startswith("worktree "):
                        wt_path = line.split("worktree ", 1)[1].strip()
                    elif line.startswith("HEAD "):
                        head = line.split("HEAD ", 1)[1].strip()
                    elif line.startswith("branch "):
                        branch = line.split("branch ", 1)[1].strip().replace("refs/heads/", "")
                    elif line.startswith("locked"):
                        is_locked = True
                        if " " in line:
                            lock_reason = line.split(" ", 1)[1].strip()

                if wt_path:
                    is_main = Path(wt_path).resolve() == git_root.resolve()
                    worktrees.append(
                        WorktreeInfo(
                            path=wt_path,
                            head_commit=head,
                            branch=branch or "detached",
                            is_main=is_main,
                            is_locked=is_locked,
                            lock_reason=lock_reason,
                        )
                    )

            return worktrees
        except Exception:
            return []

    def create_worktree(
        self,
        branch: str,
        task_id: Optional[str] = None,
        create_branch: bool = False,
        base_branch: str = "development",
    ) -> Dict[str, Any]:
        """Create a new isolated git worktree under .hath0r/worktrees/<task_id_or_slug>."""
        git_root = self._find_git_root()
        if not git_root:
            return {"success": False, "error": "Not a git repository."}

        slug = task_id or branch.replace("/", "-").replace(":", "-")
        target_dir = git_root / ".hath0r" / "worktrees" / slug
        target_dir.parent.mkdir(parents=True, exist_ok=True)

        if target_dir.exists():
            return {
                "success": False,
                "error": f"Worktree target path already exists: {target_dir}",
                "path": str(target_dir),
            }

        cmd = ["git", "worktree", "add"]
        if create_branch:
            cmd.extend(["-b", branch, str(target_dir), base_branch])
        else:
            cmd.extend([str(target_dir), branch])

        try:
            res = subprocess.run(
                cmd,
                cwd=str(git_root),
                capture_output=True,
                text=True,
            )
            if res.returncode != 0:
                # If branch checkout failed, try creating branch from base
                if "already exists" not in res.stderr and not create_branch:
                    cmd_new = ["git", "worktree", "add", "-b", branch, str(target_dir), base_branch]
                    res2 = subprocess.run(cmd_new, cwd=str(git_root), capture_output=True, text=True)
                    if res2.returncode == 0:
                        return {
                            "success": True,
                            "path": str(target_dir),
                            "branch": branch,
                            "task_id": slug,
                            "created_new_branch": True,
                        }
                return {"success": False, "error": res.stderr.strip() or res.stdout.strip()}

            return {
                "success": True,
                "path": str(target_dir),
                "branch": branch,
                "task_id": slug,
                "created_new_branch": create_branch,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def remove_worktree(self, target: str, force: bool = False) -> Dict[str, Any]:
        """Remove a git worktree by path or task ID."""
        git_root = self._find_git_root()
        if not git_root:
            return {"success": False, "error": "Not a git repository."}

        # Resolve path or slug
        resolved_path: Optional[Path] = None
        p = Path(target)
        if p.is_dir() and (p / ".git").exists():
            resolved_path = p.resolve()
        else:
            cand = git_root / ".hath0r" / "worktrees" / target
            if cand.is_dir():
                resolved_path = cand.resolve()

        cmd = ["git", "worktree", "remove"]
        if force:
            cmd.append("--force")

        if resolved_path:
            cmd.append(str(resolved_path))
        else:
            cmd.append(target)

        try:
            res = subprocess.run(cmd, cwd=str(git_root), capture_output=True, text=True)
            if res.returncode != 0:
                # Manual fallback cleanup if git worktree remove refused due to deleted files
                if resolved_path and resolved_path.exists() and force:
                    shutil.rmtree(resolved_path, ignore_errors=True)
                    subprocess.run(["git", "worktree", "prune"], cwd=str(git_root), capture_output=True)
                    return {"success": True, "path": str(resolved_path), "pruned": True}
                return {"success": False, "error": res.stderr.strip() or res.stdout.strip()}

            # Prune stale metadata
            subprocess.run(["git", "worktree", "prune"], cwd=str(git_root), capture_output=True)
            return {"success": True, "path": str(resolved_path or target)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def prune_worktrees(self) -> Dict[str, Any]:
        """Prune working tree administrative records."""
        git_root = self._find_git_root()
        if not git_root:
            return {"success": False, "error": "Not a git repository."}

        try:
            res = subprocess.run(["git", "worktree", "prune", "-v"], cwd=str(git_root), capture_output=True, text=True)
            return {"success": True, "output": res.stdout.strip()}
        except Exception as e:
            return {"success": False, "error": str(e)}
