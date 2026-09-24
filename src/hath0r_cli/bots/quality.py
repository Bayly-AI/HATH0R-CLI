"""Quality / preflight / deploy-test / release bots for PR and release gates."""

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
BRANCH_REGEX = re.compile(
    r"^(feature|bugfix|hotfix|enhancement|research|fix|chore)/(\d+)-([a-z0-9-]+)$"
)
SEMVER_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)(?:-([a-zA-Z0-9.]+))?$")


def run_cmd(args: List[str], cwd: Optional[Path] = None) -> Tuple[int, str, str]:
    """Execute command safely and capture output."""
    try:
        proc = subprocess.run(args, cwd=cwd, capture_output=True, text=True, check=False)
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
    except Exception as exc:
        return 1, "", str(exc)

# Default hard-gate check name fragments (case-insensitive substring match)
DEFAULT_HARD_GATES = (
    "SonarCloud Quality Gate",
    "validate-promotion-path",
    "pr-workflow-guard",
)

DEFAULT_PRE_DEPLOY_COMMANDS = (
    ["python", "-m", "pytest", "-q"],
    ["python", "-m", "ruff", "check", "src"],
)

DEFAULT_POST_DEPLOY_COMMANDS: tuple[list[str], ...] = ()


def _load_json_cfg(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _repo_cfg(cwd: Path) -> dict[str, Any]:
    """Load optional cfg/quality-gates.json from repo root."""
    return _load_json_cfg(cwd / "cfg" / "quality-gates.json")


@dataclass
class QualityGateBot:
    """Aggregate PR quality gates including SonarCloud hard stop."""

    cwd: Path = field(default_factory=Path.cwd)

    def evaluate_rollup(
        self,
        status_checks: List[Dict[str, Any]] | None,
        *,
        hard_gate_names: List[str] | None = None,
    ) -> Dict[str, Any]:
        """Evaluate GitHub statusCheckRollup entries against hard gates."""
        cfg = _repo_cfg(self.cwd)
        gates = hard_gate_names or cfg.get("hard_gates") or list(DEFAULT_HARD_GATES)
        rollup = status_checks or []

        def _name(c: dict[str, Any]) -> str:
            return str(c.get("name") or c.get("context") or "")

        def _failed(c: dict[str, Any]) -> bool:
            return c.get("conclusion") in (
                "FAILURE",
                "TIMED_OUT",
                "STARTUP_FAILURE",
                "CANCELLED",
            ) or c.get("state") in ("FAILURE", "ERROR")

        def _pending(c: dict[str, Any]) -> bool:
            conclusion = c.get("conclusion")
            state = c.get("state")
            return conclusion in (None, "NEUTRAL", "ACTION_REQUIRED") or state in (
                "PENDING",
                "EXPECTED",
                "QUEUED",
                "IN_PROGRESS",
            )

        failing = [_name(c) for c in rollup if _failed(c) and _name(c)]
        pending = [_name(c) for c in rollup if _pending(c) and _name(c) and not _failed(c)]
        passing = [
            _name(c)
            for c in rollup
            if _name(c)
            and not _failed(c)
            and not _pending(c)
        ]

        hard_failures = []
        hard_missing = []
        hard_pending = []
        for gate in gates:
            gate_l = gate.lower()
            matches = [c for c in rollup if gate_l in _name(c).lower()]
            if not matches:
                hard_missing.append(gate)
                continue
            if any(_failed(c) for c in matches):
                hard_failures.append(gate)
            elif any(_pending(c) for c in matches):
                hard_pending.append(gate)

        passed = len(hard_failures) == 0 and len(hard_missing) == 0 and len(failing) == 0
        # Pending hard gates block merge but are not "failed"
        ready = passed and len(hard_pending) == 0 and len(pending) == 0

        return {
            "success": ready,
            "passed": passed and len(hard_pending) == 0,
            "ready_to_merge": ready,
            "hard_gates": gates,
            "hard_failures": hard_failures,
            "hard_missing": hard_missing,
            "hard_pending": hard_pending,
            "failing_checks": failing,
            "pending_checks": pending,
            "passing_checks": passing,
            "total_checks": len(rollup),
            "message": (
                "All quality gates passed."
                if ready
                else "Quality gates not satisfied (see hard_failures/hard_missing/pending)."
            ),
        }

    def check_pr(
        self,
        pr_number: int,
        *,
        repo: Optional[str] = None,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        if dry_run:
            return {
                "success": True,
                "dry_run": True,
                "pr_number": pr_number,
                "ready_to_merge": True,
                "action": f"[DRY-RUN] Evaluate quality gates for PR #{pr_number}",
            }

        cmd = [
            "gh",
            "pr",
            "view",
            str(pr_number),
            "--json",
            "number,title,state,mergeable,statusCheckRollup,baseRefName,headRefName",
        ]
        if repo:
            cmd.extend(["--repo", repo])
        code, out, err = run_cmd(cmd, cwd=self.cwd)
        if code != 0:
            return {"success": False, "pr_number": pr_number, "error": err or out}

        try:
            pr = json.loads(out)
        except Exception as exc:
            return {"success": False, "pr_number": pr_number, "error": str(exc)}

        evaluation = self.evaluate_rollup(pr.get("statusCheckRollup") or [])
        evaluation["pr_number"] = pr_number
        evaluation["title"] = pr.get("title")
        evaluation["mergeable"] = pr.get("mergeable")
        evaluation["base"] = pr.get("baseRefName")
        evaluation["head"] = pr.get("headRefName")
        return evaluation

    def report_json(self, evaluation: Dict[str, Any]) -> str:
        return json.dumps(evaluation, indent=2, sort_keys=True)


@dataclass
class PreflightBot:
    """Pre-PR threshold bot — block opening a PR until local gates pass."""

    cwd: Path = field(default_factory=Path.cwd)

    def _current_branch(self) -> Tuple[bool, str, str]:
        rc, out, err = run_cmd(["git", "branch", "--show-current"], cwd=self.cwd)
        if rc != 0 or not out.strip():
            return False, "", err or "detached HEAD"
        return True, out.strip(), ""

    def _version_ok(self) -> Dict[str, Any]:
        version_path = self.cwd / "VERSION"
        if not version_path.is_file():
            return {"ok": False, "check": "version", "error": "VERSION file missing at repo root"}
        raw = version_path.read_text(encoding="utf-8").strip()
        if not SEMVER_RE.match(raw):
            return {"ok": False, "check": "version", "error": f"VERSION '{raw}' is not valid SemVer"}
        return {"ok": True, "check": "version", "version": raw}

    def _branch_ok(self) -> Dict[str, Any]:
        ok, branch, err = self._current_branch()
        if not ok:
            return {"ok": False, "check": "branch", "error": err}
        if branch in CANONICAL_BRANCHES:
            return {
                "ok": False,
                "check": "branch",
                "branch": branch,
                "error": f"Cannot open work PR from canonical branch '{branch}'",
            }
        if not BRANCH_REGEX.match(branch):
            return {
                "ok": False,
                "check": "branch",
                "branch": branch,
                "error": f"Branch '{branch}' violates feature|bugfix|…/<issue>-slug taxonomy",
            }
        m = BRANCH_REGEX.match(branch)
        assert m is not None
        return {
            "ok": True,
            "check": "branch",
            "branch": branch,
            "issue_number": int(m.group(2)),
            "prefix": m.group(1),
            "slug": m.group(3),
        }

    def _run_local_commands(self, commands: List[List[str]]) -> List[Dict[str, Any]]:
        results = []
        for cmd in commands:
            try:
                proc = subprocess.run(
                    cmd,
                    cwd=self.cwd,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                results.append(
                    {
                        "command": cmd,
                        "ok": proc.returncode == 0,
                        "exit_code": proc.returncode,
                        "stdout_tail": (proc.stdout or "")[-500:],
                        "stderr_tail": (proc.stderr or "")[-500:],
                    }
                )
            except FileNotFoundError as exc:
                results.append({"command": cmd, "ok": False, "error": str(exc)})
        return results

    def run(
        self,
        *,
        skip_tests: bool = False,
        dry_run: bool = False,
        extra_commands: Optional[List[List[str]]] = None,
    ) -> Dict[str, Any]:
        cfg = _repo_cfg(self.cwd)
        enabled = cfg.get("preflight", {}).get("enabled", True)
        if not enabled:
            return {
                "success": True,
                "skipped": True,
                "message": "Preflight disabled in cfg/quality-gates.json",
            }

        if dry_run:
            return {
                "success": True,
                "dry_run": True,
                "action": "[DRY-RUN] Preflight branch + VERSION + local gates",
            }

        checks: List[Dict[str, Any]] = []
        checks.append(self._branch_ok())
        checks.append(self._version_ok())

        # Dirty tree warning (not hard fail by default)
        rc, out, _ = run_cmd(["git", "status", "--porcelain"], cwd=self.cwd)
        dirty = bool(out.strip()) if rc == 0 else False
        checks.append(
            {
                "ok": True,
                "check": "working_tree",
                "dirty": dirty,
                "message": "Working tree has uncommitted changes" if dirty else "clean",
            }
        )

        cmd_results: List[Dict[str, Any]] = []
        if not skip_tests:
            commands = extra_commands
            if commands is None:
                raw = cfg.get("preflight", {}).get("commands")
                if isinstance(raw, list) and raw:
                    commands = [list(c) if isinstance(c, list) else str(c).split() for c in raw]
                else:
                    commands = [list(c) for c in DEFAULT_PRE_DEPLOY_COMMANDS]
            cmd_results = self._run_local_commands(commands)
            for cr in cmd_results:
                checks.append(
                    {
                        "ok": bool(cr.get("ok")),
                        "check": "command",
                        "command": cr.get("command"),
                        "error": None if cr.get("ok") else (cr.get("error") or f"exit {cr.get('exit_code')}"),
                    }
                )

        hard_failures = [c for c in checks if not c.get("ok")]
        success = len(hard_failures) == 0
        return {
            "success": success,
            "passed": success,
            "checks": checks,
            "command_results": cmd_results,
            "message": "Preflight passed — safe to open PR." if success else "Preflight failed — fix gates before PR.",
        }


@dataclass
class DeployTestBot:
    """Pre/post-deploy test runner; results feed coverage/quality narrative."""

    cwd: Path = field(default_factory=Path.cwd)

    def run_pre_deploy(self, *, dry_run: bool = False) -> Dict[str, Any]:
        return self._run_phase("pre_deploy", DEFAULT_PRE_DEPLOY_COMMANDS, dry_run=dry_run)

    def run_post_deploy(
        self,
        *,
        base_url: Optional[str] = None,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        cfg = _repo_cfg(self.cwd)
        commands: List[List[str]] = []
        raw = cfg.get("post_deploy", {}).get("commands")
        if isinstance(raw, list) and raw:
            commands = [list(c) if isinstance(c, list) else str(c).split() for c in raw]
        elif base_url:
            commands = [["curl", "-fsS", "-o", "/dev/null", "-w", "%{http_code}", base_url]]
        else:
            commands = [list(c) for c in DEFAULT_POST_DEPLOY_COMMANDS]

        if not commands:
            return {
                "success": True,
                "phase": "post_deploy",
                "skipped": True,
                "message": "No post-deploy commands configured (cfg/quality-gates.json post_deploy.commands).",
            }
        return self._run_phase("post_deploy", commands, dry_run=dry_run)

    def _run_phase(
        self,
        phase: str,
        default_commands: tuple[list[str], ...] | List[List[str]],
        *,
        dry_run: bool,
    ) -> Dict[str, Any]:
        cfg = _repo_cfg(self.cwd)
        phase_cfg = cfg.get(phase, {}) if isinstance(cfg.get(phase), dict) else {}
        raw = phase_cfg.get("commands")
        if isinstance(raw, list) and raw:
            commands = [list(c) if isinstance(c, list) else str(c).split() for c in raw]
        else:
            commands = [list(c) for c in default_commands]

        if dry_run:
            return {
                "success": True,
                "dry_run": True,
                "phase": phase,
                "commands": commands,
                "action": f"[DRY-RUN] Would run {phase} commands",
            }

        results = []
        for cmd in commands:
            try:
                proc = subprocess.run(cmd, cwd=self.cwd, capture_output=True, text=True, check=False)
                results.append(
                    {
                        "command": cmd,
                        "ok": proc.returncode == 0,
                        "exit_code": proc.returncode,
                        "stdout_tail": (proc.stdout or "")[-400:],
                        "stderr_tail": (proc.stderr or "")[-400:],
                    }
                )
            except FileNotFoundError as exc:
                results.append({"command": cmd, "ok": False, "error": str(exc)})

        success = all(r.get("ok") for r in results) if results else True
        return {
            "success": success,
            "phase": phase,
            "results": results,
            "counts_toward_coverage": bool(phase_cfg.get("counts_toward_coverage", phase == "pre_deploy")),
            "message": f"{phase} {'passed' if success else 'failed'}",
        }


@dataclass
class ReleaseBot:
    """SemVer validation, release notes, git tag, and GitHub release."""

    cwd: Path = field(default_factory=Path.cwd)

    def read_version(self) -> Dict[str, Any]:
        path = self.cwd / "VERSION"
        if not path.is_file():
            return {"success": False, "error": "VERSION file missing"}
        version = path.read_text(encoding="utf-8").strip()
        if not SEMVER_RE.match(version):
            return {"success": False, "error": f"Invalid SemVer in VERSION: {version}", "version": version}
        return {"success": True, "version": version, "tag": f"v{version}"}

    def validate(self) -> Dict[str, Any]:
        ver = self.read_version()
        if not ver.get("success"):
            return ver
        changelog = self.cwd / "CHANGELOG.md"
        has_cl = changelog.is_file()
        notes_ok = has_cl and ver["version"] in changelog.read_text(encoding="utf-8")
        return {
            "success": bool(notes_ok),
            "version": ver["version"],
            "tag": ver["tag"],
            "changelog_present": has_cl,
            "changelog_mentions_version": notes_ok,
            "message": (
                "VERSION and CHANGELOG aligned."
                if notes_ok
                else "CHANGELOG.md must exist and mention the VERSION string before release."
            ),
        }

    def generate_notes(self, *, version: Optional[str] = None) -> Dict[str, Any]:
        ver_info = self.read_version()
        if not ver_info.get("success"):
            return ver_info
        version = version or str(ver_info["version"])
        changelog = self.cwd / "CHANGELOG.md"
        body = ""
        if changelog.is_file():
            text = changelog.read_text(encoding="utf-8")
            # Extract section under ## [version] or ## version
            pattern = re.compile(
                rf"^##\s*\[?{re.escape(version)}\]?[^\n]*\n(.*?)(?=^##\s|\Z)",
                re.MULTILINE | re.DOTALL,
            )
            m = pattern.search(text)
            if m:
                body = m.group(1).strip()
        if not body:
            body = f"Release {version}\n\nSee CHANGELOG.md for details."
        return {
            "success": True,
            "version": version,
            "tag": f"v{version}",
            "notes": body,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    def tag_and_release(
        self,
        *,
        repo: Optional[str] = None,
        dry_run: bool = False,
        skip_github_release: bool = False,
    ) -> Dict[str, Any]:
        validation = self.validate()
        if not validation.get("success") and not dry_run:
            return {**validation, "success": False}

        notes = self.generate_notes()
        version = notes.get("version")
        tag = notes.get("tag")
        if dry_run:
            return {
                "success": True,
                "dry_run": True,
                "version": version,
                "tag": tag,
                "action": f"[DRY-RUN] git tag {tag} && gh release create {tag}",
                "notes_preview": (notes.get("notes") or "")[:400],
            }

        # Annotated tag
        rc, out, err = run_cmd(
            ["git", "tag", "-a", str(tag), "-m", f"Release {version}"],
            cwd=self.cwd,
        )
        if rc != 0 and "already exists" not in (err or out).lower():
            return {"success": False, "error": err or out, "tag": tag}

        rc_push, out_p, err_p = run_cmd(["git", "push", "origin", str(tag)], cwd=self.cwd)
        if rc_push != 0:
            return {
                "success": False,
                "error": f"Failed to push tag: {err_p or out_p}",
                "tag": tag,
                "tagged_local": True,
            }

        release_result: Dict[str, Any] = {"tag_pushed": True}
        if not skip_github_release:
            cmd = [
                "gh",
                "release",
                "create",
                str(tag),
                "--title",
                f"v{version}",
                "--notes",
                str(notes.get("notes") or f"Release {version}"),
            ]
            if repo:
                cmd.extend(["--repo", repo])
            rc_rel, out_rel, err_rel = run_cmd(cmd, cwd=self.cwd)
            release_result["github_release"] = {
                "success": rc_rel == 0,
                "url": out_rel if rc_rel == 0 else None,
                "output": out_rel or err_rel,
            }
            if rc_rel != 0:
                return {
                    "success": False,
                    "version": version,
                    "tag": tag,
                    **release_result,
                    "error": err_rel or out_rel,
                }

        return {
            "success": True,
            "version": version,
            "tag": tag,
            **release_result,
        }
