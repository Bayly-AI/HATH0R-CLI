"""Issue Manager Bot — scans, validates, prioritizes, and manages GitHub issues.

Enforces:
1. BaylyAI organization-wide scope when no project/repo is specified.
2. Status and validity checks for issues.
3. Detailed issue descriptions on creation and updates.
4. Dependency-aware priority structuring across issues.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from hath0r_cli.bots import run_cmd

# Canonical BaylyAI active repositories (excluding archived)
DEFAULT_BAYLYAI_REPOS = [
    "Bayly-AI/1-Nation",
    "Bayly-AI/1-Nation-ATC",
    "Bayly-AI/1-Nation-ATC-Wiki",
    "Bayly-AI/1-Nation-MCP",
    "Bayly-AI/BAI-MCP",
    "Bayly-AI/Bayly-Consulting",
    "Bayly-AI/baylyai-uxp",
    "Bayly-AI/Dr-Sleep",
    "Bayly-AI/HATH0R-ATC",
    "Bayly-AI/HATH0R-Agentic-Framework",
    "Bayly-AI/HATH0R-CLI",
    "Bayly-AI/HATH0R-MCP",
    "Bayly-AI/HATH0R-POC",
    "Bayly-AI/knit-happens",
    "Bayly-AI/MG-Author-Ray-Bayly",
    "Bayly-AI/midgardmedia",
]

# Patterns detecting dependency relationships in issue descriptions
DEPENDENCY_PATTERNS = [
    re.compile(
        r"(?:depends\s+on|blocked\s+by|after|requires)\s+(?:#|https?://github\.com/[^/\s]+/[^/\s]+/issues/)(\d+)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:blocks|before|prerequisite\s+for)\s+(?:#|https?://github\.com/[^/\s]+/[^/\s]+/issues/)(\d+)",
        re.IGNORECASE,
    ),
]


def resolve_baylyai_repos(repo: Optional[str] = None) -> List[str]:
    """Return explicit repo if specified, else discover/default to all active BaylyAI repos."""
    if repo and repo.strip():
        r = repo.strip()
        if not r.startswith("Bayly-AI/") and "/" not in r:
            r = f"Bayly-AI/{r}"
        return [r]

    # Try dynamic discovery via gh cli
    code, out, _ = run_cmd(["gh", "repo", "list", "Bayly-AI", "--limit", "40", "--json", "nameWithOwner,isArchived"])
    if code == 0 and out.strip():
        try:
            data = json.loads(out)
            repos = [
                item["nameWithOwner"]
                for item in data
                if isinstance(item, dict) and not item.get("isArchived")
            ]
            if repos:
                return sorted(repos)
        except Exception:
            pass
    return list(DEFAULT_BAYLYAI_REPOS)


@dataclass
class IssueManagerBot:
    """Manages issue discovery, status validation, description quality, and dependency prioritization."""

    cwd: Path = field(default_factory=Path.cwd)

    def list_issues(
        self,
        repo: Optional[str] = None,
        state: str = "open",
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """List issues across specified repo or all active BaylyAI repositories with dependency priority structure."""
        target_repos = resolve_baylyai_repos(repo)

        if dry_run:
            return {
                "success": True,
                "dry_run": True,
                "target_repos": target_repos,
                "action": f"[DRY-RUN] Would fetch {state} issues across {len(target_repos)} repositories.",
                "total_issues": 0,
                "prioritized_issues": [],
            }

        all_issues: List[Dict[str, Any]] = []

        for r in target_repos:
            cmd = [
                "gh", "issue", "list",
                "--repo", r,
                "--state", state,
                "--json", "number,title,state,body,labels,createdAt,updatedAt,url",
                "--limit", "100",
            ]
            code, out, _ = run_cmd(cmd, cwd=self.cwd)
            if code == 0 and out.strip():
                try:
                    items = json.loads(out)
                    if isinstance(items, list):
                        for it in items:
                            it["repository"] = r
                            # Check issue status and validity
                            validation = self.validate_issue_data(it)
                            it["validation"] = validation
                            all_issues.append(it)
                except Exception:
                    continue

        # Build dependency graph and structured prioritization
        prioritized = self.structure_priorities(all_issues)

        return {
            "success": True,
            "scope": "single_repo" if repo else "all_baylyai_repos",
            "repo_count": len(target_repos),
            "repositories": target_repos,
            "total_issues": len(all_issues),
            "valid_issues": sum(1 for i in all_issues if i.get("validation", {}).get("is_valid")),
            "issues": prioritized,
        }

    def validate_issue_data(self, issue_data: Dict[str, Any]) -> Dict[str, Any]:
        """Check status of an issue and ensure it has a detailed description and valid metadata."""
        issues_findings = []
        body = (issue_data.get("body") or "").strip()
        title = (issue_data.get("title") or "").strip()
        state = (issue_data.get("state") or "").upper()

        if not title:
            issues_findings.append("Missing title")
        elif len(title) < 10:
            issues_findings.append("Title too short (< 10 chars)")

        if not body:
            issues_findings.append("Missing description/body")
        else:
            # Check description quality
            word_count = len(body.split())
            if word_count < 15:
                issues_findings.append(f"Description lacks detail ({word_count} words; minimum 15 words expected)")

            # Check for structural headings if technical issue
            has_sections = bool(re.search(r"##\s+(Summary|Scope|Acceptance|Requirements)", body, re.IGNORECASE))
            if not has_sections and word_count < 30:
                issues_findings.append("Description lacks structured sections (## Summary / Acceptance Criteria)")

        # Verify state is standard
        if state not in ("OPEN", "CLOSED"):
            issues_findings.append(f"Unrecognized state: {state}")

        is_valid = len(issues_findings) == 0
        return {
            "is_valid": is_valid,
            "status": state,
            "findings": issues_findings,
            "word_count": len(body.split()) if body else 0,
        }

    def structure_priorities(self, issues: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Organize issues into priority tiers considering dependencies, epics, blockers, and roles."""
        for issue in issues:
            body = issue.get("body") or ""
            deps: List[int] = []
            blocks: List[int] = []

            for match in DEPENDENCY_PATTERNS[0].finditer(body):
                deps.append(int(match.group(1)))
            for match in DEPENDENCY_PATTERNS[1].finditer(body):
                blocks.append(int(match.group(1)))

            issue["depends_on"] = sorted(list(set(deps)))
            issue["blocks"] = sorted(list(set(blocks)))

        # 2. Priority scoring
        # Tier 1 (Blockers/Prerequisites/High Infra/Control Tower)
        # Tier 2 (Dependencies resolved) -> Tier 3 (Independent)
        def _compute_score(item: Dict[str, Any]) -> Tuple[int, int, str]:
            title = (item.get("title") or "").lower()
            repo = item.get("repository", "")

            # Highest priority: Blockers that block other tickets or foundational control tower/contracts
            has_epic_label = any(label.get("name", "").lower() == "epic" for label in item.get("labels", []))
            is_epic = "epic" in title or has_epic_label
            is_control_tower = "hath0r-cli" in repo.lower()
            blocks_count = len(item.get("blocks", []))
            depends_count = len(item.get("depends_on", []))

            # Tier 1: Has dependents waiting on it or is foundational
            if blocks_count > 0:
                tier = 1
            elif is_control_tower and not depends_count:
                tier = 2
            elif is_epic:
                tier = 2
            elif depends_count == 0:
                tier = 3
            else:
                # Has dependencies to satisfy first
                tier = 4

            # Secondary sort: number of dependencies ascending (resolve unblocked first)
            return (tier, depends_count, item.get("updatedAt", ""))

        sorted_issues = sorted(issues, key=_compute_score)

        for rank, issue in enumerate(sorted_issues, start=1):
            tier, deps_count, _ = _compute_score(issue)
            issue["priority_rank"] = rank
            issue["priority_tier"] = tier
            issue["priority_label"] = (
                "P1-Blocker/Core" if tier == 1
                else "P2-Foundation/Epic" if tier == 2
                else "P3-Ready" if tier == 3
                else "P4-Blocked-By-Dependencies"
            )

        return sorted_issues

    def create_issue(
        self,
        repo: str,
        title: str,
        body: str,
        labels: Optional[List[str]] = None,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Create a new issue with enforced detailed description requirements."""
        target_repo = repo if ("/" in repo) else f"Bayly-AI/{repo}"
        clean_title = title.strip()
        clean_body = body.strip()

        # Validate description quality
        dummy_data = {"title": clean_title, "body": clean_body, "state": "OPEN"}
        val = self.validate_issue_data(dummy_data)
        if not val["is_valid"]:
            return {
                "success": False,
                "error": f"Issue fails quality validation: {'; '.join(val['findings'])}",
                "validation": val,
            }

        if dry_run:
            return {
                "success": True,
                "dry_run": True,
                "repo": target_repo,
                "title": clean_title,
                "body_length": len(clean_body),
                "action": f"[DRY-RUN] gh issue create --repo {target_repo} --title '{clean_title}'",
            }

        cmd = ["gh", "issue", "create", "--repo", target_repo, "--title", clean_title, "--body", clean_body]
        if labels:
            cmd.extend(["--label", ",".join(labels)])

        code, out, err = run_cmd(cmd, cwd=self.cwd)
        issue_url = out.strip()
        issue_num = None
        m = re.search(r"/issues/(\d+)", issue_url)
        if m:
            issue_num = int(m.group(1))

        return {
            "success": code == 0,
            "repo": target_repo,
            "issue_number": issue_num,
            "url": issue_url if code == 0 else None,
            "output": out or err,
        }

    def update_issue(
        self,
        repo: str,
        issue_number: int,
        title: Optional[str] = None,
        body: Optional[str] = None,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Update an existing issue, ensuring description meets detail requirements if modified."""
        target_repo = repo if ("/" in repo) else f"Bayly-AI/{repo}"

        if body is not None:
            clean_body = body.strip()
            dummy_data = {"title": title or "Existing Title", "body": clean_body, "state": "OPEN"}
            val = self.validate_issue_data(dummy_data)
            if not val["is_valid"]:
                return {
                    "success": False,
                    "error": f"Updated issue body fails quality validation: {'; '.join(val['findings'])}",
                    "validation": val,
                }

        if dry_run:
            return {
                "success": True,
                "dry_run": True,
                "repo": target_repo,
                "issue_number": issue_number,
                "action": f"[DRY-RUN] gh issue edit {issue_number} --repo {target_repo}",
            }

        cmd = ["gh", "issue", "edit", str(issue_number), "--repo", target_repo]
        if title:
            cmd.extend(["--title", title.strip()])
        if body is not None:
            cmd.extend(["--body", body.strip()])

        code, out, err = run_cmd(cmd, cwd=self.cwd)
        return {
            "success": code == 0,
            "repo": target_repo,
            "issue_number": issue_number,
            "output": out or err,
        }

    def validate_issue(
        self,
        issue_number: int,
        repo: Optional[str] = None,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Fetch and validate an issue referenced in a task, returning health status and dependency insights."""
        target_repo = repo if (repo and "/" in repo) else (f"Bayly-AI/{repo}" if repo else None)
        if dry_run:
            return {
                "success": True,
                "dry_run": True,
                "issue_number": issue_number,
                "action": f"[DRY-RUN] Validate issue #{issue_number} status, description, and dependencies",
            }

        cmd = ["gh", "issue", "view", str(issue_number), "--json", "number,title,state,body,labels,url"]
        if target_repo:
            cmd.extend(["--repo", target_repo])

        code, out, err = run_cmd(cmd, cwd=self.cwd)
        if code != 0:
            return {
                "success": False,
                "issue_number": issue_number,
                "error": err or f"Issue #{issue_number} not found.",
            }

        try:
            data = json.loads(out)
        except Exception as exc:
            return {"success": False, "issue_number": issue_number, "error": str(exc)}

        validation = self.validate_issue_data(data)

        # Parse dependencies
        body = data.get("body") or ""
        deps = [int(m.group(1)) for m in DEPENDENCY_PATTERNS[0].finditer(body)]
        blocks = [int(m.group(1)) for m in DEPENDENCY_PATTERNS[1].finditer(body)]

        return {
            "success": validation.get("is_valid", False),
            "issue_number": issue_number,
            "title": data.get("title"),
            "state": data.get("state"),
            "validation": validation,
            "depends_on": sorted(list(set(deps))),
            "blocks": sorted(list(set(blocks))),
            "message": (
                f"Issue #{issue_number} '{data.get('title')}' is valid."
                if validation.get("is_valid")
                else f"Issue #{issue_number} warning: {'; '.join(validation.get('findings', []))}"
            ),
        }
