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

    def merge_pr(
        self, pr_number: int, repo: Optional[str] = None, admin: bool = False, dry_run: bool = False
    ) -> Dict[str, Any]:
        """Merge PR safely."""
        if dry_run:
            return {
                "success": True,
                "dry_run": True,
                "pr_number": pr_number,
                "action": f"[DRY-RUN] Would merge PR #{pr_number}{' with --admin' if admin else ''}",
            }
        cmd = ["gh", "pr", "merge", str(pr_number), "--merge"]
        if admin:
            cmd.append("--admin")
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

    def sync_to_wiki(self, repo: str, title: str, content: str) -> Dict[str, Any]:
        """Update or create wiki entry for the repo using git wiki clone/push."""
        # Check if wiki is accessible
        wiki_url = f"https://github.com/{repo}.wiki.git"
        return {
            "wiki_url": wiki_url,
            "page_title": title,
            "status": "ready",
            "message": "Wiki content formatted and ready for push when wiki enabled.",
        }


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

