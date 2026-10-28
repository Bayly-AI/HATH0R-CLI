"""Rule Rollout Bot — rolls a canonical CR-* AGENTS.md section out to every repository (#528).

For each unique origin remote under a workspace root that lacks the rule on
``origin/development``, the bot prepares a scratch worktree, inserts the section,
bumps the patch SemVer (CR-SEMVER-BUMP-001), validates with ``ReleaseBot``, commits,
and (with ``publish``) opens a linked issue and pull request.
"""

from __future__ import annotations

import json
import re
import tempfile
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from hath0r_cli.bots import run_cmd

RULE_ID_RE = re.compile(r"^CR-[A-Z0-9]+(?:-[A-Z0-9]+)*-\d{3}$")
SEMVER_CORE_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")
DEFAULT_ROOT = Path("/Users/raybayly/Development")
BASE_BRANCH = "development"

CANONICAL_RULE_SECTIONS: Dict[str, Dict[str, str]] = {
    "CR-CLI-ENTRY-001": {
        "title": "Start with the CLI",
        "slug": "cli-entry-rule",
        "summary": (
            "agents check the `hath0r` operator CLI first on every request, offer to register "
            "missing capabilities, and require docs before code"
        ),
        "section": (
            "## CR-CLI-ENTRY-001: Start with the CLI (CRITICAL — Org-Wide · CANONICAL)\n\n"
            "1. **Start with the CLI (CRITICAL ENTRY GATE)**: When receiving ANY request or starting any task, "
            "agents **MUST ALWAYS START WITH THE OPERATOR CLI (`hath0r`)** rather than inventing ad-hoc scripts. "
            "Check `hath0r --help` and the matching `hath0r <group> --help` first.\n"
            "2. **Missing Capability Offer**: If the required connection, MCP, workflow, bot, or factory does not "
            "exist in `hath0r`, offer to register the missing capability, using the original request as the "
            "acceptance test.\n"
            "3. **Docs before code**: Require procedure/playbook/runbook before scaffolding implementation.\n\n"
            "Canonical: [HATH0R-CLI `docs/governance/cli-first-rules.md`]"
            "(https://github.com/Bayly-AI/HATH0R-CLI/blob/development/docs/governance/cli-first-rules.md).\n\n"
        ),
    },
}

Runner = Callable[[List[str], Optional[Path]], Tuple[int, str, str]]


def bump_patch(version: Optional[str]) -> str:
    """Return the next patch version; a repository without a version starts at 0.1.0."""
    m = SEMVER_CORE_RE.match((version or "").strip())
    if not m:
        return "0.1.0"
    major, minor, patch = (int(x) for x in m.groups())
    return f"{major}.{minor}.{patch + 1}"


def insert_section(agents_text: str, section: str) -> str:
    """Insert the section above the first ``## `` heading (or append when there is none)."""
    m = re.search(r"^## ", agents_text, re.M)
    if not m:
        return agents_text.rstrip("\n") + "\n\n" + section
    return agents_text[: m.start()] + section + agents_text[m.start() :]


def changelog_with_entry(changelog: Optional[str], version: str, entry: str) -> str:
    """Insert a version entry above the first released ``## [x`` heading (keeping ``[Unreleased]`` on top)."""
    block = f"## [{version}] - {date.today().isoformat()}\n\n### Added\n- {entry}\n\n"
    if changelog is None:
        return (
            "# Changelog\n\nAll notable changes to this project are documented in this file.\n\n"
            "The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),\n"
            "and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).\n\n" + block
        )
    m = re.search(r"^## \[\d", changelog, re.M)
    if not m:
        return changelog.rstrip("\n") + "\n\n" + block
    return changelog[: m.start()] + block + changelog[m.start() :]


def _tally(repos: List[Dict[str, Any]]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for r in repos:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    return counts


def remote_slug(url: str) -> Optional[str]:
    """``https://github.com/Owner/Repo.git`` or ``git@github.com:Owner/Repo.git`` → ``Owner/Repo``."""
    m = re.search(r"github\.com[:/]([^/]+/[^/]+?)(?:\.git)?/?$", url.strip())
    return m.group(1) if m else None


@dataclass
class RuleRolloutBot:
    """Plans, prepares, and publishes canonical rule rollouts across repositories."""

    cwd: Path = field(default_factory=Path.cwd)
    runner: Runner = field(default=run_cmd)

    def _run(self, args: List[str], cwd: Optional[Path] = None) -> Tuple[int, str, str]:
        return self.runner(args, cwd)

    def _git(self, repo: Path, *args: str) -> Tuple[int, str, str]:
        return self._run(["git", "-C", str(repo), *args])

    # ------------------------------------------------------------------ rules

    @staticmethod
    def list_rules() -> List[Dict[str, str]]:
        return [{"rule_id": rid, "title": meta["title"]} for rid, meta in sorted(CANONICAL_RULE_SECTIONS.items())]

    @staticmethod
    def resolve_rule(rule_id: str, section_file: Optional[Path | str] = None) -> Dict[str, str]:
        """Return the rule metadata, from the canonical registry or a section file."""
        if not RULE_ID_RE.match(rule_id):
            raise ValueError(f"Invalid rule id: {rule_id!r} (expected CR-<AREA>-<NAME>-NNN)")
        if section_file:
            text = Path(section_file).read_text(encoding="utf-8")
            if not re.search(rf"^## {re.escape(rule_id)}\b", text, re.M):
                raise ValueError(f"Section file must contain a '## {rule_id}' heading")
            return {
                "title": rule_id,
                "slug": rule_id.lower(),
                "summary": f"adds the canonical `{rule_id}` rule",
                "section": text.rstrip("\n") + "\n\n",
            }
        if rule_id not in CANONICAL_RULE_SECTIONS:
            known = ", ".join(sorted(CANONICAL_RULE_SECTIONS))
            raise ValueError(f"Unknown rule {rule_id}; pass --section-file or use one of: {known}")
        return dict(CANONICAL_RULE_SECTIONS[rule_id])

    # --------------------------------------------------------------- discovery

    def discover(self, root: Path) -> List[Dict[str, Any]]:
        """Repository roots under ``root`` with an origin remote, one entry per unique remote."""
        from hath0r_cli.bots.task_evaluator_bot import TaskEvaluatorBot

        seen: Dict[str, Dict[str, Any]] = {}
        no_remote: List[Dict[str, Any]] = []
        for path in TaskEvaluatorBot._discover_repos(root):
            if (path / ".git").is_file():
                continue  # linked worktree of another checkout
            code, url, _ = self._git(path, "remote", "get-url", "origin")
            slug = remote_slug(url) if code == 0 else None
            rel = str(path.relative_to(root)) if path != root else path.name
            if not slug:
                no_remote.append({"repo": rel, "path": str(path), "slug": None, "status": "no-remote"})
                continue
            seen.setdefault(slug.lower(), {"repo": rel, "path": str(path), "slug": slug})
        return sorted(seen.values(), key=lambda r: r["repo"]) + no_remote

    def _open_rule_pr(self, slug: str, rule_id: str) -> Optional[str]:
        code, out, _ = self._run(
            ["gh", "pr", "list", "-R", slug, "--state", "open", "--search", f"{rule_id} in:title", "--json", "url"]
        )
        if code != 0:
            return None
        try:
            prs = json.loads(out or "[]")
        except json.JSONDecodeError:
            return None
        return prs[0]["url"] if prs else None

    def classify(self, repo: Dict[str, Any], rule_id: str, *, check_prs: bool = True) -> Dict[str, Any]:
        """Set ``status`` to compliant / pending-pr / missing / no-agents-md / no-base-branch."""
        if repo.get("status") == "no-remote":
            return repo
        path = Path(repo["path"])
        self._git(path, "fetch", "-q", "origin", BASE_BRANCH)
        code, agents, _ = self._git(path, "show", f"origin/{BASE_BRANCH}:AGENTS.md")
        if code != 0:
            code_b, _, _ = self._git(path, "rev-parse", "-q", "--verify", f"origin/{BASE_BRANCH}")
            repo["status"] = "no-agents-md" if code_b == 0 else "no-base-branch"
            return repo
        if rule_id in agents:
            repo["status"] = "compliant"
            return repo
        pr = self._open_rule_pr(repo["slug"], rule_id) if check_prs else None
        repo["status"] = "pending-pr" if pr else "missing"
        if pr:
            repo["pr"] = pr
        return repo

    def status(self, rule_id: str, root: Optional[Path | str] = None, *, check_prs: bool = True) -> Dict[str, Any]:
        base = Path(root).resolve() if root else DEFAULT_ROOT
        repos = [self.classify(r, rule_id, check_prs=check_prs) for r in self.discover(base)]
        return {"success": True, "rule_id": rule_id, "root_dir": str(base), "counts": _tally(repos), "repos": repos}

    # ----------------------------------------------------------------- prepare

    def _bump_manifests(self, wt: Path, new: str) -> None:
        pyproject = wt / "pyproject.toml"
        if pyproject.is_file():
            text = pyproject.read_text(encoding="utf-8")
            pyproject.write_text(
                re.sub(r'^version = "[^"]+"', f'version = "{new}"', text, count=1, flags=re.M), encoding="utf-8"
            )
        package = wt / "package.json"
        if package.is_file():
            text = package.read_text(encoding="utf-8")
            package.write_text(re.sub(r'"version":\s*"[^"]+"', f'"version": "{new}"', text, count=1), encoding="utf-8")
        lock = wt / "package-lock.json"
        if lock.is_file():
            data = json.loads(lock.read_text(encoding="utf-8"))
            if "version" in data:
                data["version"] = new
            root_pkg = data.get("packages", {}).get("")
            if isinstance(root_pkg, dict) and "version" in root_pkg:
                root_pkg["version"] = new
            lock.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    def prepare(self, repo: Dict[str, Any], rule_id: str, rule: Dict[str, str], work_dir: Path) -> Dict[str, Any]:
        """Commit the rule, version bump, and CHANGELOG entry in a scratch worktree."""
        from hath0r_cli.bots.quality import ReleaseBot

        path = Path(repo["path"])
        name = re.sub(r"[^A-Za-z0-9_.-]+", "_", repo["repo"])
        wt = work_dir / name
        branch = f"chore/{rule['slug']}"
        code, _, err = self._git(path, "worktree", "add", "-q", "-B", branch, str(wt), f"origin/{BASE_BRANCH}")
        if code != 0:
            return {**repo, "status": "error", "error": f"worktree add failed: {err}"}
        repo = {**repo, "worktree": str(wt), "branch": branch}

        agents = wt / "AGENTS.md"
        agents.write_text(insert_section(agents.read_text(encoding="utf-8"), rule["section"]), encoding="utf-8")

        vfile = wt / "VERSION"
        old = vfile.read_text(encoding="utf-8").strip() if vfile.is_file() else None
        new = bump_patch(old)
        vfile.write_text(new + "\n", encoding="utf-8")
        self._bump_manifests(wt, new)
        changelog = wt / "CHANGELOG.md"
        entry = f"**`{rule_id}` ({rule['title']} — CANONICAL)** in `AGENTS.md`: {rule['summary']}."
        changelog.write_text(
            changelog_with_entry(changelog.read_text(encoding="utf-8") if changelog.is_file() else None, new, entry),
            encoding="utf-8",
        )
        repo.update({"old_version": old, "new_version": new})

        validation = ReleaseBot(cwd=wt).validate()
        if not validation.get("success"):
            return {**repo, "status": "error", "error": f"release validate failed: {validation.get('message')}"}

        self._git(wt, "add", "AGENTS.md", "VERSION", "CHANGELOG.md")
        for manifest in ("pyproject.toml", "package.json", "package-lock.json"):
            if (wt / manifest).is_file():
                self._git(wt, "add", manifest)
        message = f"docs(agents): add {rule_id} {rule['title']} rule\n\nBump version {old or '(none)'} -> {new}.\n"
        code, out, err = self._git(wt, "commit", "-q", "-m", message)
        if code != 0:
            return {**repo, "status": "error", "error": f"commit failed (hooks are never bypassed): {err or out}"}
        return {**repo, "status": "prepared"}

    # ----------------------------------------------------------------- publish

    def publish(self, repo: Dict[str, Any], rule_id: str, rule: Dict[str, str]) -> Dict[str, Any]:
        """Open the issue, rename the branch to ``chore/<issue>-<slug>``, push, and open the PR."""
        from hath0r_cli.bots.issue_manager import IssueManagerBot

        wt = Path(repo["worktree"])
        title = f"Add {rule_id} ({rule['title']}) to AGENTS.md"
        issue_body = (
            f"Add the canonical {rule_id} rule to the root AGENTS.md: {rule['summary']}. "
            "Bump the patch SemVer and CHANGELOG per CR-SEMVER-BUMP-001. Opened by hath0r rules ensure-all."
        )
        issue = IssueManagerBot(cwd=wt).create_issue(repo=repo["slug"], title=title, body=issue_body)
        number = issue.get("issue_number")
        if not issue.get("success") or not number:
            return {**repo, "status": "error", "error": f"issue create failed: {issue.get('error')}"}
        branch = f"chore/{number}-{rule['slug']}"
        self._git(wt, "branch", "-M", branch)
        code, _, err = self._git(wt, "push", "-q", "-u", "origin", branch)
        if code != 0:
            return {**repo, "status": "error", "issue": number, "error": f"push failed: {err}"}
        body = (
            f"## Summary\n- Adds the canonical **{rule_id}** rule to `AGENTS.md`: {rule['summary']}.\n"
            f"- Bumps `VERSION` **{repo.get('old_version') or '(none)'} → {repo['new_version']}**, keeping "
            "package manifests and `CHANGELOG.md` in step (CR-SEMVER-BUMP-001).\n\n"
            f"Closes #{number}\n\n**Version Impact: patch**\n\n"
            "## Test plan\n- `hath0r release validate` passes (VERSION is SemVer and matches CHANGELOG).\n"
            "- Docs and version metadata only; no code paths change.\n\n"
            "_Opened by `hath0r rules ensure-all`._\n"
        )
        code, url, err = self._run(
            [
                "gh",
                "pr",
                "create",
                "-R",
                repo["slug"],
                "--base",
                BASE_BRANCH,
                "--head",
                branch,
                "--title",
                f"docs(agents): add {rule_id} {rule['title']} rule (#{number})",
                "--body",
                body,
            ],
            wt,
        )
        if code != 0:
            return {**repo, "status": "error", "issue": number, "branch": branch, "error": f"pr create failed: {err}"}
        return {**repo, "status": "published", "issue": number, "branch": branch, "pr": url.strip()}

    # -------------------------------------------------------------- ensure-all

    def _roll_out(
        self,
        repo: Dict[str, Any],
        rule_id: str,
        rule: Dict[str, str],
        work_dir: Path,
        *,
        publish: bool,
        keep_worktree: bool,
    ) -> Dict[str, Any]:
        """Prepare (and optionally publish) one repository, removing its worktree unless kept or failed."""
        work_dir.mkdir(parents=True, exist_ok=True)
        res = self.prepare(repo, rule_id, rule, work_dir)
        if publish and res["status"] == "prepared":
            res = self.publish(res, rule_id, rule)
        if res.get("worktree") and not keep_worktree and res["status"] != "error":
            self._git(Path(repo["path"]), "worktree", "remove", "--force", res["worktree"])
            res.pop("worktree")
        return res

    def ensure_all(
        self,
        rule_id: str,
        *,
        root: Optional[Path | str] = None,
        section_file: Optional[Path | str] = None,
        apply: bool = False,
        publish: bool = False,
        work_dir: Optional[Path | str] = None,
        keep_worktrees: bool = False,
    ) -> Dict[str, Any]:
        """Preview (default), prepare (``apply``), or publish (``publish``) the rollout of ``rule_id``."""
        try:
            rule = self.resolve_rule(rule_id, section_file)
        except (ValueError, OSError) as exc:
            return {"success": False, "rule_id": rule_id, "error": str(exc), "repos": []}
        apply = apply or publish
        plan = self.status(rule_id, root)
        wdir: Optional[Path] = None
        if apply:
            wdir = Path(work_dir) if work_dir else Path(tempfile.mkdtemp(prefix=f"hath0r-rules-{rule_id.lower()}-"))
        results: List[Dict[str, Any]] = []
        for repo in plan["repos"]:
            if wdir is None or repo["status"] != "missing":
                results.append(repo)
            else:
                results.append(self._roll_out(repo, rule_id, rule, wdir, publish=publish, keep_worktree=keep_worktrees))
        counts = _tally(results)
        mode = "preview"
        if publish:
            mode = "publish"
        elif apply:
            mode = "apply"
        return {
            "success": counts.get("error", 0) == 0,
            "rule_id": rule_id,
            "mode": mode,
            "root_dir": plan["root_dir"],
            "work_dir": str(wdir) if wdir else None,
            "counts": counts,
            "repos": results,
        }


__all__ = [
    "CANONICAL_RULE_SECTIONS",
    "RuleRolloutBot",
    "bump_patch",
    "changelog_with_entry",
    "insert_section",
    "remote_slug",
]
