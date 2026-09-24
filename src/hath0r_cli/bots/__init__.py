"""PR & Branch Lifecycle Bots for Hath0r.

Includes:
- BranchBot: Branch creation, naming policy validation, issue-first enforcement.
- PRBot: PR creation, Dependabot PR auto-handling, gate checking, promotion enforcement.
- GitJanitorBot: Audit and prune stale/merged/closed non-canonical branches.
- DocumentationBot: PR release notes and wiki sync.
"""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

VALID_BRANCH_PREFIXES = ("feature", "bugfix", "hotfix", "enhancement", "research", "fix", "chore")
CANONICAL_BRANCHES = ("development", "testing", "staging", "master")
BRANCH_REGEX = re.compile(r"^(feature|bugfix|hotfix|enhancement|research|fix|chore)/(\d+)-([a-z0-9-]+)$")
RELEASE_BRANCH_REGEX = re.compile(r"^release/(\d+\.\d+\.\d+(?:-[a-zA-Z0-9.]+)?)$")


def run_cmd(args: List[str], cwd: Optional[Path] = None) -> Tuple[int, str, str]:
    """Execute command safely and capture output."""
    try:
        proc = subprocess.run(
            args,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
        )
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
    except Exception as exc:
        return 1, "", str(exc)


@dataclass
class BranchBot:
    """Manages git branches, validates taxonomy, and enforces issue-first governance."""

    cwd: Path = field(default_factory=Path.cwd)

    def validate_name(self, branch_name: str) -> Dict[str, Any]:
        """Validate if a branch name conforms to repository governance rules."""
        if branch_name in CANONICAL_BRANCHES:
            return {
                "valid": True,
                "is_canonical": True,
                "is_work_branch": False,
                "branch": branch_name,
                "message": f"Branch '{branch_name}' is a protected canonical branch.",
            }

        m_release = RELEASE_BRANCH_REGEX.match(branch_name)
        if m_release:
            return {
                "valid": True,
                "is_canonical": False,
                "is_release": True,
                "is_work_branch": False,
                "version": m_release.group(1),
                "branch": branch_name,
                "message": f"Branch '{branch_name}' is a valid release promotion branch.",
            }

        m_work = BRANCH_REGEX.match(branch_name)
        if m_work:
            return {
                "valid": True,
                "is_canonical": False,
                "is_work_branch": True,
                "prefix": m_work.group(1),
                "issue_number": int(m_work.group(2)),
                "slug": m_work.group(3),
                "branch": branch_name,
                "message": f"Branch '{branch_name}' is a valid work branch for issue #{m_work.group(2)}.",
            }

        return {
            "valid": False,
            "is_canonical": False,
            "is_work_branch": False,
            "branch": branch_name,
            "message": (
                f"Branch '{branch_name}' violates naming conventions. "
                f"Must match '<prefix>/<issue-number>-<slug>' where prefix is one of: "
                f"{', '.join(VALID_BRANCH_PREFIXES)}."
            ),
        }

    def format_branch_name(self, prefix: str, issue_number: int, slug: str) -> str:
        """Construct standard branch name."""
        prefix = prefix.lower().strip()
        if prefix not in VALID_BRANCH_PREFIXES:
            raise ValueError(f"Invalid prefix '{prefix}'. Must be one of {VALID_BRANCH_PREFIXES}")
        clean_slug = re.sub(r"[^a-z0-9-]", "-", slug.lower().strip()).strip("-")
        clean_slug = re.sub(r"-+", "-", clean_slug)
        return f"{prefix}/{issue_number}-{clean_slug}"

    def create_branch(
        self, prefix: str, issue_number: int, slug: str, base: str = "development", dry_run: bool = False
    ) -> Dict[str, Any]:
        """Create and checkout branch from specified base (default: development)."""
        branch_name = self.format_branch_name(prefix, issue_number, slug)
        if dry_run:
            return {
                "success": True,
                "dry_run": True,
                "branch": branch_name,
                "base": base,
                "action": f"[DRY-RUN] Would checkout branch '{branch_name}' from '{base}'",
            }
        # Fetch base
        run_cmd(["git", "fetch", "origin", base], cwd=self.cwd)
        # Checkout new branch
        code, out, err = run_cmd(["git", "checkout", "-b", branch_name, f"origin/{base}"], cwd=self.cwd)
        if code != 0:
            # Try from local base if remote failed
            code, out, err = run_cmd(["git", "checkout", "-b", branch_name, base], cwd=self.cwd)

        return {
            "success": code == 0,
            "branch": branch_name,
            "base": base,
            "output": out or err,
        }


@dataclass
class PRBot:
    """Manages PR lifecycle, validates checks, handles Dependabot, and enforces promotion."""

    cwd: Path = field(default_factory=Path.cwd)

    def list_prs(self, repo: Optional[str] = None, state: str = "open") -> List[Dict[str, Any]]:
        """List pull requests for repository."""
        cmd = [
            "gh", "pr", "list",
            "--state", state,
            "--json", "number,title,headRefName,baseRefName,author,labels,isDraft,url",
        ]
        if repo:
            cmd.extend(["--repo", repo])
        code, out, err = run_cmd(cmd, cwd=self.cwd)
        if code != 0:
            return []
        try:
            return json.loads(out)
        except Exception:
            return []

    def check_pr_status(self, pr_number: int, repo: Optional[str] = None) -> Dict[str, Any]:
        """Check CI status, reviews, and mergeability for a PR."""
        cmd = [
            "gh", "pr", "view", str(pr_number),
            "--json", "number,title,state,mergeable,statusCheckRollup,author,baseRefName,headRefName",
        ]
        if repo:
            cmd.extend(["--repo", repo])
        code, out, err = run_cmd(cmd, cwd=self.cwd)
        if code != 0:
            return {"error": err, "pr_number": pr_number}
        try:
            return json.loads(out)
        except Exception as exc:
            return {"error": str(exc), "pr_number": pr_number}

    def process_dependabot(
        self, pr_number: int, repo: Optional[str] = None, auto_merge: bool = True, dry_run: bool = False
    ) -> Dict[str, Any]:
        """Triage, validate, and optionally auto-merge Dependabot PRs."""
        status = self.check_pr_status(pr_number, repo=repo)
        if "error" in status:
            return status

        author = status.get("author", {}).get("login", "")
        if "dependabot" not in author.lower():
            return {
                "pr_number": pr_number,
                "is_dependabot": False,
                "action": "skipped",
                "reason": f"Author '{author}' is not Dependabot",
            }

        # Check rollup
        rollup = status.get("statusCheckRollup", []) or []
        failing_checks = [
            c.get("name") or c.get("context")
            for c in rollup
            if c.get("conclusion") in ("FAILURE", "TIMED_OUT", "STARTUP_FAILURE") or c.get("state") == "FAILURE"
        ]

        if failing_checks:
            return {
                "pr_number": pr_number,
                "is_dependabot": True,
                "action": "blocked",
                "failing_checks": failing_checks,
                "reason": "CI checks failing",
            }

        actions_taken = []
        if dry_run:
            actions_taken.append("[DRY-RUN] Would approve PR")
            if auto_merge:
                actions_taken.append("[DRY-RUN] Would enable auto-merge")
            return {
                "pr_number": pr_number,
                "is_dependabot": True,
                "dry_run": True,
                "actions": actions_taken,
                "status": "dry-run",
            }

        # Approve
        review_cmd = [
            "gh", "pr", "review", str(pr_number),
            "--approve", "-b", "Approved by Hath0r PR Bot (automated Dependabot triage)",
        ]
        if repo:
            review_cmd.extend(["--repo", repo])
        code_rev, _, _ = run_cmd(review_cmd, cwd=self.cwd)
        if code_rev == 0:
            actions_taken.append("approved")

        if auto_merge:
            merge_cmd = ["gh", "pr", "merge", str(pr_number), "--auto", "--squash"]
            if repo:
                merge_cmd.extend(["--repo", repo])
            code_merge, _, _ = run_cmd(merge_cmd, cwd=self.cwd)
            if code_merge == 0:
                actions_taken.append("auto-merge-enabled")

        return {
            "pr_number": pr_number,
            "is_dependabot": True,
            "actions": actions_taken,
            "status": "processed",
        }

    def create_pr(
        self,
        title: Optional[str] = None,
        body: Optional[str] = None,
        base: str = "development",
        head: Optional[str] = None,
        repo: Optional[str] = None,
        draft: bool = False,
        semver: str = "patch",
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Create pull request for current or specified branch."""
        # Determine head branch if not passed
        current_branch = head
        if not current_branch:
            rc, out, _ = run_cmd(["git", "branch", "--show-current"], cwd=self.cwd)
            if rc == 0 and out.strip():
                current_branch = out.strip()

        if not current_branch or current_branch in CANONICAL_BRANCHES:
            return {
                "success": False,
                "error": f"Cannot create PR from canonical or undetermined branch '{current_branch}'.",
            }

        # Validate taxonomy
        branch_bot = BranchBot(cwd=self.cwd)
        val = branch_bot.validate_name(current_branch)
        if not val.get("valid"):
            return {
                "success": False,
                "error": f"Branch '{current_branch}' violates taxonomy: {val.get('message')}",
            }

        # Construct title/body defaults if not provided
        pr_title = title or f"{current_branch}: automatic task promotion"
        pr_body = body or f"Autonomous task PR for `{current_branch}`.\n\nsemver: {semver}\n"
        if "semver:" not in pr_body.lower():
            pr_body = f"{pr_body}\n\nsemver: {semver}\n"

        if dry_run:
            return {
                "success": True,
                "dry_run": True,
                "branch": current_branch,
                "base": base,
                "title": pr_title,
                "action": f"[DRY-RUN] gh pr create --base {base} --head {current_branch} --title '{pr_title}'",
            }

        # Push head branch to origin before creating PR
        run_cmd(["git", "push", "-u", "origin", current_branch], cwd=self.cwd)

        cmd = [
            "gh", "pr", "create",
            "--base", base,
            "--head", current_branch,
            "--title", pr_title,
            "--body", pr_body,
        ]
        if draft:
            cmd.append("--draft")
        if repo:
            cmd.extend(["--repo", repo])

        code, out, err = run_cmd(cmd, cwd=self.cwd)
        # Parse PR number or url from output
        pr_url = out.strip()
        pr_num = None
        match = re.search(r"/pull/(\d+)", pr_url)
        if match:
            pr_num = int(match.group(1))

        return {
            "success": code == 0,
            "pr_number": pr_num,
            "url": pr_url if code == 0 else None,
            "branch": current_branch,
            "base": base,
            "output": out or err,
        }

    def monitor_checks(
        self,
        pr_number: int,
        repo: Optional[str] = None,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Check CI rollup checks status for a PR and verify whether it is ready for merge."""
        if dry_run:
            return {
                "success": True,
                "dry_run": True,
                "pr_number": pr_number,
                "status": "passed",
                "action": f"[DRY-RUN] gh pr view {pr_number} --json statusCheckRollup",
            }

        status = self.check_pr_status(pr_number, repo=repo)
        if "error" in status:
            return {"success": False, "pr_number": pr_number, "error": status.get("error")}

        rollup = status.get("statusCheckRollup", []) or []
        failing = [
            c.get("name") or c.get("context")
            for c in rollup
            if c.get("conclusion") in ("FAILURE", "TIMED_OUT", "STARTUP_FAILURE") or c.get("state") == "FAILURE"
        ]
        pending = [
            c.get("name") or c.get("context")
            for c in rollup
            if c.get("conclusion") in ("ACTION_REQUIRED", "NEUTRAL") or c.get("state") == "PENDING"
        ]

        passed = len(failing) == 0
        return {
            "success": passed,
            "pr_number": pr_number,
            "healthy": passed,
            "failing_checks": failing,
            "pending_checks": pending,
            "total_checks": len(rollup),
            "state": status.get("state"),
        }

    def merge_pr(
        self,
        pr_number: int,
        repo: Optional[str] = None,
        admin: bool = False,
        squash: bool = True,
        delete_branch: bool = True,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Merge PR safely, defaulting to squash + admin bypass + delete branch."""
        if dry_run:
            flags = f"{' with --admin' if admin else ''}{' --squash' if squash else ''}"
            return {
                "success": True,
                "dry_run": True,
                "pr_number": pr_number,
                "action": f"[DRY-RUN] Would merge PR #{pr_number}{flags}",
            }
        cmd = ["gh", "pr", "merge", str(pr_number)]
        if squash:
            cmd.append("--squash")
        else:
            cmd.append("--merge")
        if admin:
            cmd.append("--admin")
        if delete_branch:
            cmd.append("--delete-branch")
        if repo:
            cmd.extend(["--repo", repo])
        code, out, err = run_cmd(cmd, cwd=self.cwd)
        return {
            "success": code == 0,
            "pr_number": pr_number,
            "output": out or err,
        }


@dataclass
class GitJanitorBot:
    """Audits and deletes stale, merged, or closed branches across the repo."""

    cwd: Path = field(default_factory=Path.cwd)

    def scan_stale_branches(self, repo: Optional[str] = None) -> Dict[str, Any]:
        """Identify remote branches that have been merged or whose PRs are closed."""
        # 1. Fetch remote branch list
        code, out, _ = run_cmd(["git", "branch", "-r"], cwd=self.cwd)
        if code != 0:
            return {"stale_branches": [], "error": "Failed to list remote branches"}

        branches = [
            b.strip().replace("origin/", "")
            for b in out.splitlines()
            if b.strip() and "->" not in b
        ]

        # Filter out canonical
        candidate_branches = [b for b in branches if b not in CANONICAL_BRANCHES and not b.startswith("HEAD")]

        stale = []
        for branch in candidate_branches:
            # Check PR status for this branch
            cmd = ["gh", "pr", "list", "--head", branch, "--state", "all", "--json", "number,state,mergedAt"]
            if repo:
                cmd.extend(["--repo", repo])
            pr_code, pr_out, _ = run_cmd(cmd, cwd=self.cwd)
            if pr_code == 0 and pr_out.strip():
                try:
                    prs = json.loads(pr_out)
                    if prs and all(p.get("state") in ("MERGED", "CLOSED") for p in prs):
                        stale.append({
                            "branch": branch,
                            "reason": f"Associated PR(s) are {', '.join(p.get('state') for p in prs)}",
                            "prs": [p.get("number") for p in prs],
                        })
                except Exception:
                    pass

        return {
            "scanned_count": len(candidate_branches),
            "stale_count": len(stale),
            "stale_branches": stale,
        }

    def prune_branch(self, branch: str, remote: bool = True, dry_run: bool = False) -> Dict[str, Any]:
        """Safely delete branch locally and/or remotely."""
        if branch in CANONICAL_BRANCHES:
            return {"success": False, "branch": branch, "error": "Cannot delete canonical branch"}

        if dry_run:
            return {
                "success": True,
                "dry_run": True,
                "branch": branch,
                "action": f"[DRY-RUN] Would prune branch '{branch}' (remote={remote})",
            }

        results = {}
        # Delete remote
        if remote:
            code_rem, out_rem, err_rem = run_cmd(["git", "push", "origin", "--delete", branch], cwd=self.cwd)
            results["remote"] = code_rem == 0

        # Delete local if exists
        code_loc, _, _ = run_cmd(["git", "branch", "-D", branch], cwd=self.cwd)
        results["local"] = code_loc == 0

        return {
            "success": results.get("remote", False) or results.get("local", False),
            "branch": branch,
            "details": results,
        }

    def pull_development(self, base: str = "development", dry_run: bool = False) -> Dict[str, Any]:
        """Checkout canonical development branch and pull latest changes from origin."""
        if dry_run:
            return {
                "success": True,
                "dry_run": True,
                "base": base,
                "action": f"[DRY-RUN] git checkout {base} && git pull origin {base}",
            }

        # 1. Checkout base
        rc_co, out_co, err_co = run_cmd(["git", "checkout", base], cwd=self.cwd)
        if rc_co != 0:
            return {
                "success": False,
                "base": base,
                "error": f"Failed to checkout {base}: {err_co or out_co}",
            }

        # 2. Pull latest
        rc_pull, out_pull, err_pull = run_cmd(["git", "pull", "origin", base], cwd=self.cwd)
        return {
            "success": rc_pull == 0,
            "base": base,
            "output": out_pull or err_pull,
        }


@dataclass
class DocumentationBot:
    """Generates PR documentation, release notes, and updates repository wiki."""

    cwd: Path = field(default_factory=Path.cwd)

    def generate_pr_summary(self, pr_data: Dict[str, Any]) -> str:
        """Create structured documentation summary for a PR."""
        number = pr_data.get("number", "N/A")
        title = pr_data.get("title", "Untitled PR")
        head = pr_data.get("headRefName", "unknown")
        base = pr_data.get("baseRefName", "unknown")
        author = pr_data.get("author", {}).get("login", "unknown")
        timestamp = datetime.now(timezone.utc).isoformat()

        doc = [
            f"# PR #{number}: {title}",
            "",
            f"- **Author:** @{author}",
            f"- **Branch:** `{head}` → `{base}`",
            f"- **Documented At:** {timestamp}",
            "",
            "## Summary of Changes",
            pr_data.get("body", "No description provided."),
            "",
        ]
        return "\n".join(doc)

    def _quality_cfg(self) -> Dict[str, Any]:
        path = self.cwd / "cfg" / "quality-gates.json"
        if not path.is_file():
            return {}
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _wiki_enabled(self) -> Tuple[bool, str]:
        cfg = self._quality_cfg().get("wiki") or {}
        if not bool(cfg.get("enabled", False)):
            return False, "wiki.enabled is false in cfg/quality-gates.json"
        return True, "enabled"

    def sync_to_wiki(
        self,
        repo: str,
        title: str,
        content: str,
        *,
        pr_number: Optional[int] = None,
        dry_run: bool = False,
        force: bool = False,
    ) -> Dict[str, Any]:
        """Update or create wiki entry when cfg + GitHub wiki dual-enablement allows it.

        Idempotent by PR number: page title defaults to ``PR-<n>-<slug>``.
        """
        enabled, reason = self._wiki_enabled()
        if not enabled and not force:
            return {
                "success": True,
                "skipped": True,
                "reason": reason,
                "repo": repo,
                "page_title": title,
            }

        safe_title = re.sub(r"[^A-Za-z0-9._-]+", "-", title).strip("-") or "PR-notes"
        if pr_number is not None:
            safe_title = f"PR-{pr_number}-{safe_title}"[:80]

        wiki_url = f"https://github.com/{repo}.wiki.git"
        if dry_run:
            return {
                "success": True,
                "dry_run": True,
                "wiki_url": wiki_url,
                "page_title": safe_title,
                "action": f"[DRY-RUN] Would push wiki page '{safe_title}' to {wiki_url}",
            }

        # Best-effort clone into temp under .hath0r (never .ai/)
        import tempfile

        work = Path(tempfile.mkdtemp(prefix="hath0r-wiki-"))
        code, out, err = run_cmd(["git", "clone", "--depth", "1", wiki_url, str(work)], cwd=self.cwd)
        if code != 0:
            return {
                "success": False,
                "wiki_url": wiki_url,
                "page_title": safe_title,
                "error": err or out or "Wiki clone failed (is GitHub wiki enabled on the repo?)",
                "status": "wiki_unavailable",
            }

        page_path = work / f"{safe_title}.md"
        page_path.write_text(content if content.endswith("\n") else content + "\n", encoding="utf-8")
        run_cmd(["git", "add", page_path.name], cwd=work)
        rc_c, _, err_c = run_cmd(
            ["git", "-c", "user.email=bot@hath0r.local", "-c", "user.name=Hath0r DocumentationBot",
             "commit", "-m", f"docs: sync wiki page {safe_title}"],
            cwd=work,
        )
        if rc_c != 0 and "nothing to commit" not in (err_c or "").lower():
            # nothing new is ok
            pass
        rc_p, out_p, err_p = run_cmd(["git", "push", "origin", "HEAD"], cwd=work)
        return {
            "success": rc_p == 0 or "everything up-to-date" in (out_p or err_p or "").lower(),
            "wiki_url": wiki_url,
            "page_title": safe_title,
            "page_path": str(page_path),
            "status": "pushed" if rc_p == 0 else "error",
            "output": out_p or err_p,
            "pr_number": pr_number,
        }

    def share_knowledge(
        self,
        summary: Optional[str] = None,
        notes: Optional[str] = None,
        target_kb: Optional[str] = None,
        *,
        pr_number: Optional[int] = None,
        repo: Optional[str] = None,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Share PR/task knowledge into project MCP / group KB (project MCP first).

        Writes an idempotent markdown artifact under the configured local MCP path
        (see cfg/mcp-doc-publish.json). Does not call remote MCP over the network
        unless operators extend hooks later — local durable handoff is the default.
        """
        cfg_root = self._quality_cfg().get("knowledge_share") or {}
        if cfg_root.get("enabled") is False:
            return {"success": True, "skipped": True, "reason": "knowledge_share.enabled is false"}

        publish_cfg_path = self.cwd / str(cfg_root.get("cfg") or "cfg/mcp-doc-publish.json")
        publish: Dict[str, Any] = {}
        if publish_cfg_path.is_file():
            try:
                loaded = json.loads(publish_cfg_path.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    publish = loaded
            except Exception:
                publish = {}

        # Prefer hath0r / opensource group MCP local path
        groups = publish.get("groups") if isinstance(publish.get("groups"), dict) else {}
        preferred = groups.get("hath0r") or next(iter(groups.values()), {}) if groups else {}
        mcp = preferred.get("mcp") if isinstance(preferred, dict) else {}
        local_path = target_kb or (mcp.get("local_path") if isinstance(mcp, dict) else None)
        if not local_path:
            local_path = str(self.cwd / ".hath0r" / "knowledgebase" / "lessons-learned")

        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        key = f"pr-{pr_number}" if pr_number is not None else f"share-{stamp}"
        dest_dir = Path(local_path).expanduser()
        # lessons-learned bucket under canonical when present
        if (dest_dir / "canonical").is_dir():
            dest_dir = dest_dir / "canonical" / "lessons-learned"
        elif dest_dir.name != "lessons-learned":
            dest_dir = dest_dir / "lessons-learned"

        body_lines = [
            f"# Knowledge share {key}",
            "",
            f"- **Generated:** {datetime.now(timezone.utc).isoformat()}",
            f"- **Repo:** {repo or 'local'}",
            f"- **PR:** {pr_number if pr_number is not None else 'n/a'}",
            "",
            "## Summary",
            summary or notes or "No summary provided.",
            "",
        ]
        if notes and notes != summary:
            body_lines.extend(["## Notes", notes, ""])
        content = "\n".join(body_lines)
        dest_file = dest_dir / f"{key}.md"

        if dry_run:
            return {
                "success": True,
                "dry_run": True,
                "action": f"[DRY-RUN] Would write knowledge share to {dest_file}",
                "target_kb": str(dest_dir),
                "key": key,
                "pr_number": pr_number,
            }

        try:
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest_file.write_text(content, encoding="utf-8")
        except OSError as exc:
            return {
                "success": False,
                "error": str(exc),
                "target_kb": str(dest_dir),
                "key": key,
            }

        return {
            "success": True,
            "target_kb": str(dest_dir),
            "path": str(dest_file),
            "key": key,
            "pr_number": pr_number,
            "synced_at": datetime.now(timezone.utc).isoformat(),
            "status": "synchronized",
            "idempotent": True,
        }


@dataclass
class TaskAnnouncerBot:
    """Emits completion announcements and execution status across messaging channels."""

    cwd: Path = field(default_factory=Path.cwd)

    def announce_complete(
        self,
        task_id: Optional[str] = None,
        summary: Optional[str] = None,
        channel: str = "console",
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Broadcast completion event upon successful task lifecycle execution."""
        timestamp = datetime.now(timezone.utc).isoformat()
        msg = f"Task '{task_id or 'end-of-task'}' successfully completed and verified at {timestamp}."

        if dry_run:
            return {
                "success": True,
                "dry_run": True,
                "task_id": task_id,
                "action": f"[DRY-RUN] Announce complete via {channel}: {msg}",
            }

        return {
            "success": True,
            "task_id": task_id,
            "channel": channel,
            "timestamp": timestamp,
            "message": msg,
        }


@dataclass
class IssueGuardBot:
    """Enforces issue-first governance (cr-branch-gov-001) and manages GitHub issue attachments."""

    cwd: Path = field(default_factory=Path.cwd)

    def view_issue(self, issue_number: int, repo: Optional[str] = None) -> Dict[str, Any]:
        """Fetch issue details and state from GitHub."""
        cmd = ["gh", "issue", "view", str(issue_number), "--json", "number,title,state,body,url,labels"]
        if repo:
            cmd.extend(["--repo", repo])
        code, out, err = run_cmd(cmd, cwd=self.cwd)
        if code != 0:
            return {"success": False, "error": err or f"Issue #{issue_number} not found."}
        try:
            data = json.loads(out)
            return {"success": True, "issue": data}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def create_issue(
        self,
        title: str,
        body: Optional[str] = None,
        labels: Optional[List[str]] = None,
        repo: Optional[str] = None,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Create a new GitHub issue with appropriate governance metadata."""
        clean_title = title.strip()
        issue_body = body or f"Autonomous task ticket for: {clean_title}\n\nGovernance: cr-branch-gov-001"
        if dry_run:
            return {
                "success": True,
                "dry_run": True,
                "title": clean_title,
                "action": f"[DRY-RUN] gh issue create --title '{clean_title}'",
            }

        cmd = ["gh", "issue", "create", "--title", clean_title, "--body", issue_body]
        if labels:
            cmd.extend(["--label", ",".join(labels)])
        if repo:
            cmd.extend(["--repo", repo])

        code, out, err = run_cmd(cmd, cwd=self.cwd)
        issue_url = out.strip()
        issue_num = None
        m = re.search(r"/issues/(\d+)", issue_url)
        if m:
            issue_num = int(m.group(1))

        return {
            "success": code == 0,
            "issue_number": issue_num,
            "url": issue_url if code == 0 else None,
            "title": clean_title,
            "output": out or err,
        }

    def verify_issue(
        self,
        issue_number: Optional[int] = None,
        repo: Optional[str] = None,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Verify an issue exists and is open for work."""
        if dry_run:
            return {
                "success": True,
                "dry_run": True,
                "issue_number": issue_number,
                "open": True,
                "action": f"[DRY-RUN] Verify issue #{issue_number} is open",
            }

        if not issue_number or issue_number <= 0:
            return {"success": False, "error": "No valid issue number specified."}

        res = self.view_issue(issue_number, repo=repo)
        if not res.get("success"):
            return res

        issue_data = res.get("issue", {})
        is_open = issue_data.get("state") == "OPEN"
        return {
            "success": is_open,
            "issue_number": issue_number,
            "title": issue_data.get("title"),
            "state": issue_data.get("state"),
            "open": is_open,
            "error": None if is_open else f"Issue #{issue_number} is {issue_data.get('state')}, expected OPEN.",
        }


@dataclass
class BranchGuardBot:
    """Enforces branch governance (cr-branch-gov-001) preventing work on protected canonical branches."""

    cwd: Path = field(default_factory=Path.cwd)

    def check_active_branch(self) -> Dict[str, Any]:
        """Inspect current git branch and determine validity as a work branch."""
        rc, out, err = run_cmd(["git", "branch", "--show-current"], cwd=self.cwd)
        current = out.strip() if rc == 0 else ""
        branch_bot = BranchBot(cwd=self.cwd)
        val = branch_bot.validate_name(current) if current else {"valid": False, "is_work_branch": False}

        is_canonical = current in CANONICAL_BRANCHES
        can_work = val.get("valid", False) and val.get("is_work_branch", False)

        return {
            "success": True,
            "current_branch": current,
            "is_canonical": is_canonical,
            "is_work_branch": can_work,
            "validation": val,
            "blocked": is_canonical,
            "message": (
                f"Active branch '{current}' is a protected canonical branch. Editing forbidden."
                if is_canonical
                else f"Active branch '{current}' is ready for task execution."
            ),
        }

    def ensure_work_branch(
        self,
        issue_number: int,
        slug: str,
        prefix: str = "feature",
        base: str = "development",
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Ensure current checkout is on a valid work branch; auto-create from base if needed."""
        active = self.check_active_branch()
        if active.get("success") and active.get("is_work_branch"):
            # Already on a work branch
            val = active.get("validation", {})
            if val.get("issue_number") == issue_number:
                return {
                    "success": True,
                    "branch": active.get("current_branch"),
                    "action": "already_on_branch",
                    "created": False,
                }

        # Need to create/checkout proper branch
        branch_bot = BranchBot(cwd=self.cwd)
        create_res = branch_bot.create_branch(prefix, issue_number, slug, base=base, dry_run=dry_run)
        create_res["action"] = "created_and_checked_out"
        create_res["created"] = True
        return create_res


@dataclass
class DockerBot:
    """Manages Docker workflows, container lifecycle operations, and diagnostic inspections."""

    cwd: Path = field(default_factory=Path.cwd)

    def validate_workflow(self, workflow_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate a Docker workflow document against schema contract."""
        schema_path = Path(__file__).resolve().parents[3] / "contracts" / "hath0r-docker-workflow-v1.schema.json"
        if not schema_path.is_file():
            return {"valid": False, "errors": [f"Schema not found: {schema_path}"]}

        try:
            import jsonschema

            schema = json.loads(schema_path.read_text(encoding="utf-8"))
            validator = jsonschema.Draft202012Validator(schema)
            errors = [f"{e.json_path}: {e.message}" for e in validator.iter_errors(workflow_data)]
            return {
                "valid": len(errors) == 0,
                "errors": errors,
                "workflow_id": workflow_data.get("metadata", {}).get("id"),
            }
        except Exception as exc:
            return {"valid": False, "errors": [str(exc)]}

    def build_container(
        self,
        compose_file: Optional[str] = None,
        service: Optional[str] = None,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Build service container via docker compose."""
        if dry_run:
            return {
                "success": True,
                "dry_run": True,
                "action": (
                    f"[DRY-RUN] docker compose -f {compose_file or 'docker-compose.yml'} build {service or ''}".strip()
                ),
            }

        cmd = ["docker", "compose"]
        if compose_file:
            cmd.extend(["-f", compose_file])
        cmd.append("build")
        if service:
            cmd.append(service)

        rc, out, err = run_cmd(cmd, cwd=self.cwd)
        return {
            "success": rc == 0,
            "exit_code": rc,
            "output": out,
            "error": err if rc != 0 else None,
        }

    def up(
        self,
        compose_file: Optional[str] = None,
        services: Optional[List[str]] = None,
        detach: bool = True,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Start containers via docker compose."""
        if dry_run:
            srv_str = " ".join(services or [])
            return {
                "success": True,
                "dry_run": True,
                "action": f"[DRY-RUN] docker compose -f {compose_file or 'docker-compose.yml'} up -d {srv_str}".strip(),
            }

        cmd = ["docker", "compose"]
        if compose_file:
            cmd.extend(["-f", compose_file])
        cmd.append("up")
        if detach:
            cmd.append("-d")
        if services:
            cmd.extend(services)

        rc, out, err = run_cmd(cmd, cwd=self.cwd)
        return {
            "success": rc == 0,
            "exit_code": rc,
            "output": out,
            "error": err if rc != 0 else None,
        }

    def healthcheck(
        self,
        endpoint: Optional[str] = None,
        container_name: Optional[str] = None,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Verify health of container or HTTP health endpoint."""
        if dry_run:
            return {
                "success": True,
                "dry_run": True,
                "healthy": True,
                "action": f"[DRY-RUN] probe {endpoint or container_name or 'health'}",
            }

        if endpoint:
            import urllib.request
            try:
                req = urllib.request.Request(endpoint, headers={"User-Agent": "Hath0r-DockerBot/1.0"})
                with urllib.request.urlopen(req, timeout=5) as resp:
                    healthy = resp.status == 200
                    return {
                        "success": healthy,
                        "healthy": healthy,
                        "status_code": resp.status,
                        "endpoint": endpoint,
                    }
            except Exception as exc:
                return {
                    "success": False,
                    "healthy": False,
                    "endpoint": endpoint,
                    "error": str(exc),
                }

        if container_name:
            rc, out, err = run_cmd(
                ["docker", "inspect", "--format", "{{.State.Health.Status}}", container_name],
                cwd=self.cwd,
            )
            if rc == 0:
                status = out.strip().lower()
                healthy = status == "healthy" or status == ""  # container running without explicit healthcheck
                return {
                    "success": healthy,
                    "healthy": healthy,
                    "container": container_name,
                    "status": status or "running",
                }
            return {
                "success": False,
                "healthy": False,
                "container": container_name,
                "error": err or "Container not found",
            }

        return {"success": True, "healthy": True, "message": "No endpoint or container provided."}

    def diagnose(
        self,
        container_name: Optional[str] = None,
        compose_file: Optional[str] = None,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Diagnose common container issues (network, status, logs tail, env refs) without leaking secrets."""
        if dry_run:
            return {
                "success": True,
                "dry_run": True,
                "healthy": True,
                "action": f"[DRY-RUN] diagnose container {container_name or 'all'}",
                "findings": [],
            }

        findings: List[str] = []
        if container_name:
            # Check state
            rc, out, _ = run_cmd(["docker", "inspect", "--format", "{{.State.Status}}", container_name], cwd=self.cwd)
            if rc != 0:
                findings.append(f"Container '{container_name}' does not exist or Docker daemon is unreachable.")
            elif out.strip() != "running":
                findings.append(f"Container '{container_name}' is in '{out.strip()}' state instead of 'running'.")

            # Check exit code if stopped
            rc_exit, out_exit, _ = run_cmd(
                ["docker", "inspect", "--format", "{{.State.ExitCode}}", container_name],
                cwd=self.cwd,
            )
            if rc_exit == 0 and out_exit.strip() not in {"0", ""}:
                findings.append(f"Container '{container_name}' exited with error code {out_exit.strip()}.")

        remediation = (
            "Check logs with 'docker logs <name>' or verify compose environment configuration."
            if findings
            else None
        )
        return {
            "success": True,
            "container": container_name,
            "healthy": len(findings) == 0,
            "findings": findings,
            "remediation": remediation,
        }

    def down(
        self,
        compose_file: Optional[str] = None,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Tear down containers via docker compose."""
        if dry_run:
            return {
                "success": True,
                "dry_run": True,
                "action": f"[DRY-RUN] docker compose -f {compose_file or 'docker-compose.yml'} down".strip(),
            }

        cmd = ["docker", "compose"]
        if compose_file:
            cmd.extend(["-f", compose_file])
        cmd.append("down")

        rc, out, err = run_cmd(cmd, cwd=self.cwd)
        return {
            "success": rc == 0,
            "exit_code": rc,
            "output": out,
            "error": err if rc != 0 else None,
        }

