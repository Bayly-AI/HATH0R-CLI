"""GitWorkflowBot — branch, PR and environment-promotion workflows (CR-BAI-001 / cr-branch-gov-001).

Mirrors the rules enforced in CI by ``.github/workflows/enforce-promotion-path.yml`` so operators
and agents get the same verdict locally *before* pushing:

    issue → <type>/<issue>-slug → development
    release/x.y.z (cut from development) | development → testing → staging → master (production)

Staging and master are human-gated. Promotion PRs are merged with a merge commit (never squash)
so the push gate's ancestry check (``origin/<prev>`` is an ancestor of the target) keeps holding.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from hath0r_cli.bots import IssueGuardBot, run_cmd

PROMOTION_CHAIN = ("development", "testing", "staging", "master")
STAGE_ENVIRONMENTS = {"testing": "testing", "staging": "staging", "master": "production"}
HUMAN_GATED_STAGES = ("staging", "master")
TARGET_ALIASES = {"production": "master", "prod": "master", "main": "master", "test": "testing", "stage": "staging"}
WORK_TYPES = ("feature", "bugfix", "hotfix", "enhancement", "research", "fix", "chore")

# Same expressions as enforce-promotion-path.yml so local and CI verdicts never disagree.
WORK_BRANCH_RE = re.compile(rf"^({'|'.join(WORK_TYPES)})/([0-9]+)-[A-Za-z0-9][A-Za-z0-9._-]*$")
RELEASE_BRANCH_RE = re.compile(r"^release/([0-9]+\.[0-9]+\.[0-9]+(?:[.-][A-Za-z0-9._-]+)?)$")
SEMVER_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+(?:[.-][A-Za-z0-9._-]+)?$")
GATE_WORKFLOW = "promotion-environment-gates.yml"
MAX_LISTED_COMMITS = 50


def normalize_stage(name: str) -> str:
    """Map friendly aliases (production, prod, main, …) onto canonical branch names."""
    key = (name or "").strip().lower()
    return TARGET_ALIASES.get(key, key)


def previous_stage(target: str) -> Optional[str]:
    """Return the stage that feeds ``target`` in the promotion chain (None for development)."""
    target = normalize_stage(target)
    if target not in PROMOTION_CHAIN or target == PROMOTION_CHAIN[0]:
        return None
    return PROMOTION_CHAIN[PROMOTION_CHAIN.index(target) - 1]


@dataclass
class GitWorkflowBot:
    """Plans and executes branch, PR and promotion workflows against the canonical chain."""

    cwd: Path = field(default_factory=Path.cwd)
    remote: str = "origin"

    # ------------------------------------------------------------------ policy

    def check_path(self, head: str, base: str) -> Dict[str, Any]:
        """Decide whether a PR ``head → base`` is allowed (pure; mirrors CI)."""
        base = normalize_stage(base)
        res: Dict[str, Any] = {
            "head": head,
            "base": base,
            "allowed": False,
            "classification": None,
            "human_gate": base in HUMAN_GATED_STAGES,
            "environment": STAGE_ENVIRONMENTS.get(base),
            "issue_number": None,
            "merge_strategy": "squash" if base == "development" else "merge",
        }
        is_release = bool(RELEASE_BRANCH_RE.match(head))

        def deny(reason: str) -> Dict[str, Any]:
            res["reason"] = reason
            return res

        def allow(classification: str, reason: str) -> Dict[str, Any]:
            res.update(allowed=True, classification=classification, reason=reason)
            return res

        if base == "development":
            if head in PROMOTION_CHAIN:
                return deny(f"PRs into development cannot come from canonical branch '{head}'.")
            if is_release:
                return deny("release/* branches must not PR into development; promote release → testing.")
            m = WORK_BRANCH_RE.match(head)
            if not m:
                return deny(
                    f"Invalid work branch '{head}'. Required: <type>/<issue>-slug with type in {', '.join(WORK_TYPES)}."
                )
            res["issue_number"] = int(m.group(2))
            return allow("feature-work", f"Work branch for issue #{m.group(2)} may target development.")
        if base == "testing":
            if head == "development" or is_release:
                return allow("promote-testing", "testing accepts development or release/x.y.z.")
            return deny(f"PRs into testing must come from development or release/x.y.z (got '{head}').")
        if base == "staging":
            if head == "testing" or is_release:
                return allow("human-gate-promotion", "staging accepts testing or release/x.y.z (human gate).")
            return deny(f"PRs into staging must come from testing or release/x.y.z (got '{head}').")
        if base == "master":
            if head == "staging" or is_release:
                return allow("human-gate-promotion", "master accepts staging or release/x.y.z (human gate).")
            return deny(f"PRs into master (production) must come from staging or release/x.y.z (got '{head}').")
        return deny(f"Unsupported base branch '{base}'. Expected one of {', '.join(PROMOTION_CHAIN)}.")

    # ------------------------------------------------------------------ git helpers

    def _git(self, *args: str) -> tuple[int, str, str]:
        return run_cmd(["git", *args], cwd=self.cwd)

    def _gh(self, *args: str) -> tuple[int, str, str]:
        return run_cmd(["gh", *args], cwd=self.cwd)

    def current_branch(self) -> str:
        rc, out, _ = self._git("branch", "--show-current")
        return out.strip() if rc == 0 else ""

    def fetch(self, *refs: str) -> bool:
        rc, _, _ = self._git("fetch", "--quiet", self.remote, *refs)
        return rc == 0

    def _remote_ref(self, branch: str) -> str:
        return f"{self.remote}/{branch}"

    def _ref_exists(self, ref: str) -> bool:
        rc, _, _ = self._git("rev-parse", "--verify", "--quiet", ref)
        return rc == 0

    def ahead_behind(self, source: str, target: str) -> Optional[Dict[str, int]]:
        """Commits ``source`` has that ``target`` lacks (pending) and vice versa (drift)."""
        src, dst = self._remote_ref(source), self._remote_ref(target)
        if not (self._ref_exists(src) and self._ref_exists(dst)):
            return None
        rc, out, _ = self._git("rev-list", "--left-right", "--count", f"{dst}...{src}")
        if rc != 0 or not out.strip():
            return None
        drift, pending = (int(x) for x in out.split())
        return {"pending": pending, "drift": drift}

    def _commits_between(self, source: str, target: str) -> List[str]:
        rc, out, _ = self._git(
            "log", "--oneline", "--no-decorate", f"-{MAX_LISTED_COMMITS}",
            f"{self._remote_ref(target)}..{self._remote_ref(source)}",
        )
        return [line for line in out.splitlines() if line.strip()] if rc == 0 else []

    def _version_at(self, branch: str) -> Optional[str]:
        rc, out, _ = self._git("show", f"{self._remote_ref(branch)}:VERSION")
        return (out.strip() or None) if rc == 0 else None

    def _open_pr(self, head: str, base: str) -> Optional[Dict[str, Any]]:
        rc, out, _ = self._gh(
            "pr", "list", "--state", "open", "--head", head, "--base", base, "--json", "number,url,title"
        )
        if rc != 0:
            return None
        try:
            prs = json.loads(out or "[]")
        except json.JSONDecodeError:
            return None
        return prs[0] if prs else None

    # ------------------------------------------------------------------ status

    def status(self, fetch: bool = True) -> Dict[str, Any]:
        """Promotion pipeline snapshot: pending/drift per stage, release branches, open promotion PRs."""
        fetched = self.fetch(*PROMOTION_CHAIN) if fetch else None
        stages: List[Dict[str, Any]] = []
        for src, dst in zip(PROMOTION_CHAIN, PROMOTION_CHAIN[1:]):
            counts = self.ahead_behind(src, dst)
            stages.append(
                {
                    "from": src,
                    "to": dst,
                    "environment": STAGE_ENVIRONMENTS[dst],
                    "human_gate": dst in HUMAN_GATED_STAGES,
                    "pending_commits": counts["pending"] if counts else None,
                    "drift_commits": counts["drift"] if counts else None,
                    "source_version": self._version_at(src),
                    "target_version": self._version_at(dst),
                    "open_pr": self._open_pr(src, dst),
                    "resolved": counts is not None,
                }
            )
        rc, out, _ = self._git("branch", "-r", "--list", f"{self.remote}/release/*", "--format=%(refname:short)")
        releases = [r.removeprefix(f"{self.remote}/") for r in out.splitlines() if r.strip()] if rc == 0 else []
        current = self.current_branch()
        return {
            "success": all(s["resolved"] for s in stages),
            "fetched": fetched,
            "current_branch": current,
            "current_branch_kind": self._branch_kind(current),
            "chain": list(PROMOTION_CHAIN),
            "stages": stages,
            "release_branches": releases,
        }

    def _branch_kind(self, branch: str) -> str:
        if branch in PROMOTION_CHAIN:
            return "canonical"
        if RELEASE_BRANCH_RE.match(branch):
            return "release"
        if WORK_BRANCH_RE.match(branch):
            return "work"
        return "invalid" if branch else "detached"

    # ------------------------------------------------------------------ branch workflows

    def sync_branch(self, base: str = "development", rebase: bool = False, dry_run: bool = False) -> Dict[str, Any]:
        """Bring the current work branch up to date with ``origin/<base>``; aborts cleanly on conflict."""
        current = self.current_branch()
        res: Dict[str, Any] = {"branch": current, "base": base, "strategy": "rebase" if rebase else "merge"}
        if not current or current in PROMOTION_CHAIN:
            return {**res, "success": False, "error": f"Refusing to sync canonical/detached branch '{current}'."}
        rc, out, _ = self._git("status", "--porcelain", "--untracked-files=no")
        if rc == 0 and out.strip():
            return {**res, "success": False, "error": "Working tree has uncommitted changes; commit or stash first."}
        action = ["rebase", self._remote_ref(base)] if rebase else ["merge", "--no-edit", self._remote_ref(base)]
        if dry_run:
            return {**res, "success": True, "dry_run": True, "action": f"git fetch {self.remote} {base} && git {' '.join(action)}"}
        if not self.fetch(base):
            return {**res, "success": False, "error": f"Could not fetch {self.remote}/{base}."}
        counts = self.ahead_behind(base, current) if self._ref_exists(self._remote_ref(current)) else None
        rc, out, err = self._git(*action)
        if rc != 0:
            _, conflicts, _ = self._git("diff", "--name-only", "--diff-filter=U")
            self._git("rebase" if rebase else "merge", "--abort")
            return {
                **res,
                "success": False,
                "conflicts": [c for c in conflicts.splitlines() if c],
                "error": f"{res['strategy']} of {self.remote}/{base} hit conflicts and was aborted; resolve manually.",
                "output": err or out,
            }
        return {**res, "success": True, "output": out or err, "remote_counts": counts}

    def start_branch(
        self,
        work_type: str,
        issue_number: int,
        slug: str,
        base: str = "development",
        verify_issue: bool = True,
        repo: Optional[str] = None,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Create ``<type>/<issue>-slug`` from ``origin/<base>`` after confirming the issue is open."""
        from hath0r_cli.bots import BranchBot

        branch_bot = BranchBot(cwd=self.cwd)
        try:
            name = branch_bot.format_branch_name(work_type, issue_number, slug)
        except ValueError as exc:
            return {"success": False, "error": str(exc)}
        issue: Dict[str, Any] = {"skipped": True}
        if verify_issue:
            issue = IssueGuardBot(cwd=self.cwd).verify_issue(issue_number, repo=repo, dry_run=dry_run)
            if not issue.get("success"):
                return {"success": False, "branch": name, "issue": issue, "error": issue.get("error")}
        rc, out, _ = self._git("rev-parse", "--verify", "--quiet", f"refs/heads/{name}")
        if rc == 0 and not dry_run:
            return {"success": False, "branch": name, "error": f"Branch '{name}' already exists locally."}
        res = branch_bot.create_branch(work_type, issue_number, slug, base=base, dry_run=dry_run)
        res["issue"] = issue
        return res

    # ------------------------------------------------------------------ promotion workflows

    def cut_release(self, version: str, base: str = "development", dry_run: bool = False) -> Dict[str, Any]:
        """Create and push ``release/<version>`` from ``origin/<base>`` without touching the checkout."""
        version = version.strip().removeprefix("v")
        branch = f"release/{version}"
        res: Dict[str, Any] = {"branch": branch, "base": base, "version": version}
        if not SEMVER_RE.match(version):
            return {**res, "success": False, "error": f"'{version}' is not a SemVer version (x.y.z)."}
        push_ref = f"{self._remote_ref(base)}:refs/heads/{branch}"
        if dry_run:
            return {**res, "success": True, "dry_run": True, "action": f"git push {self.remote} {push_ref}"}
        if not self.fetch(base):
            return {**res, "success": False, "error": f"Could not fetch {self.remote}/{base}."}
        rc, out, _ = self._git("ls-remote", "--heads", self.remote, branch)
        if rc == 0 and out.strip():
            return {**res, "success": False, "error": f"{branch} already exists on {self.remote}."}
        base_version = self._version_at(base)
        rc, out, err = self._git("push", self.remote, push_ref)
        if rc != 0:
            return {**res, "success": False, "error": err or out}
        self.fetch(branch)
        warning = None
        if base_version and base_version != version:
            warning = f"VERSION on {base} is {base_version}, not {version}; bump before promoting."
        return {**res, "success": True, "base_version": base_version, "warning": warning, "output": err or out}

    def _promotion_body(self, source: str, target: str, version: Optional[str], commits: List[str]) -> str:
        env = STAGE_ENVIRONMENTS[target]
        gate = target in HUMAN_GATED_STAGES
        lines = [
            "## Promotion",
            f"- `{source}` → **{target}** (environment: `{env}`){' — HUMAN GATE' if gate else ''}",
            "",
            "## Version",
            f"- SemVer: `{version or 'unknown'}`",
            f"- Release branch: `{source}`" if RELEASE_BRANCH_RE.match(source) else "- Release branch: n/a",
            "",
            f"## Commits ({len(commits)}{'+' if len(commits) >= MAX_LISTED_COMMITS else ''})",
            *[f"- {c}" for c in commits],
            "",
            "## Validation already done",
            f"- [ ] `{source}` deploy/smoke passed",
            "",
        ]
        if gate:
            lines += [
                "## Human gate",
                "- [ ] Human initiator:",
                f"- [ ] Environment approval (`{env}`)",
                "- [ ] Not bot-only approval",
                "",
            ]
        lines += [
            "Merge with a **merge commit** (not squash) to keep the promotion ancestry gate green.",
            "",
            "Policy: CR-BAI-001 · cr-branch-gov-001 · generated by `hath0r promote to`",
        ]
        return "\n".join(lines)

    def promote(
        self,
        target: str,
        source: Optional[str] = None,
        draft: bool = False,
        trigger_gate: bool = False,
        repo: Optional[str] = None,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Open (or reuse) the promotion PR ``source → target`` and optionally fire the environment gate."""
        target = normalize_stage(target)
        source = source or previous_stage(target)
        res: Dict[str, Any] = {"target": target, "source": source, "environment": STAGE_ENVIRONMENTS.get(target)}
        if target not in STAGE_ENVIRONMENTS or not source:
            return {**res, "success": False, "error": f"Promotion target must be one of {', '.join(STAGE_ENVIRONMENTS)} (or production)."}
        path = self.check_path(source, target)
        res["path"] = path
        if not path["allowed"]:
            return {**res, "success": False, "error": path["reason"]}
        self.fetch(source, target)
        counts = self.ahead_behind(source, target)
        if counts is None:
            return {**res, "success": False, "error": f"Could not resolve {self.remote}/{source} and {self.remote}/{target}."}
        res["pending_commits"], res["drift_commits"] = counts["pending"], counts["drift"]
        if counts["pending"] == 0:
            return {**res, "success": True, "noop": True, "message": f"{target} already contains everything in {source}."}
        commits = self._commits_between(source, target)
        version = self._version_at(source)
        title = f"Promote {source} → {target}" + (f" (v{version})" if version else "")
        body = self._promotion_body(source, target, version, commits)
        res.update(title=title, version=version, commits=commits, human_gate=path["human_gate"])

        gh_create = ["pr", "create", "--base", target, "--head", source, "--title", title, "--body", body]
        if draft:
            gh_create.append("--draft")
        if repo:
            gh_create += ["--repo", repo]
        gate_cmd = ["workflow", "run", GATE_WORKFLOW, "-f", f"target_environment={STAGE_ENVIRONMENTS[target]}", "-f", f"ref_name={source}"]
        if repo:
            gate_cmd += ["--repo", repo]
        if dry_run:
            planned = [f"gh pr create --base {target} --head {source} --title '{title}'"]
            if trigger_gate:
                planned.append("gh " + " ".join(gate_cmd))
            return {**res, "success": True, "dry_run": True, "body": body, "actions": planned}

        existing = self._open_pr(source, target)
        if existing:
            res.update(pr_number=existing.get("number"), url=existing.get("url"), reused=True)
        else:
            rc, out, err = self._gh(*gh_create)
            if rc != 0:
                return {**res, "success": False, "error": err or out}
            m = re.search(r"/pull/(\d+)", out)
            res.update(pr_number=int(m.group(1)) if m else None, url=out.strip(), reused=False)

        if trigger_gate:
            if not (self.cwd / ".github" / "workflows" / GATE_WORKFLOW).exists():
                res["gate"] = {"triggered": False, "error": f"{GATE_WORKFLOW} not present in this repository."}
            else:
                rc, out, err = self._gh(*gate_cmd)
                res["gate"] = {"triggered": rc == 0, "output": out or err}
        return {**res, "success": True}

    # ------------------------------------------------------------------ PR merge

    def merge(
        self,
        pr_number: int,
        human_approved: bool = False,
        repo: Optional[str] = None,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Merge a PR with the policy-correct strategy; staging/master need ``human_approved``."""
        view = ["pr", "view", str(pr_number), "--json", "baseRefName,headRefName,state,mergeable,url"]
        if repo:
            view += ["--repo", repo]
        rc, out, err = self._gh(*view)
        if rc != 0:
            return {"success": False, "pr_number": pr_number, "error": err or out or "gh pr view failed"}
        info = json.loads(out)
        base, head = info.get("baseRefName", ""), info.get("headRefName", "")
        path = self.check_path(head, base)
        res: Dict[str, Any] = {"pr_number": pr_number, "base": base, "head": head, "url": info.get("url"), "path": path}
        if info.get("state") != "OPEN":
            return {**res, "success": False, "error": f"PR #{pr_number} is {info.get('state')}."}
        if not path["allowed"]:
            return {**res, "success": False, "error": path["reason"]}
        if path["human_gate"] and not human_approved:
            return {
                **res,
                "success": False,
                "error": f"{base} is human-gated (CR-BAI-001). Re-run with --human-approved after a human review.",
            }
        strategy = path["merge_strategy"]
        cmd = ["pr", "merge", str(pr_number), f"--{strategy}"]
        # Never delete canonical/release heads; work branches are disposable after squash.
        if base == "development":
            cmd.append("--delete-branch")
        if repo:
            cmd += ["--repo", repo]
        res["strategy"] = strategy
        if dry_run:
            return {**res, "success": True, "dry_run": True, "action": "gh " + " ".join(cmd)}
        rc, out, err = self._gh(*cmd)
        return {**res, "success": rc == 0, "output": out or err, **({} if rc == 0 else {"error": err or out})}
