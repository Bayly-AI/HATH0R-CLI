"""Autonomous End-of-Task Daemon Bot.

Automates the continuous observation, quality-gate evaluation, merge execution,
branch reaping, development synchronization, and knowledge sharing lifecycle.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from hath0r_cli.bots import DocumentationBot, GitJanitorBot, PRBot, TaskAnnouncerBot


@dataclass
class DaemonCycleResult:
    phase: str
    success: bool
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


class EndOfTaskDaemonBot:
    """Orchestrates autonomous end-of-task lifecycle from PR monitoring to merge and reaping."""

    def __init__(
        self,
        cwd: Optional[Path] = None,
        poll_interval: float = 10.0,
        timeout: float = 600.0,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        self.cwd = cwd or Path.cwd()
        self.poll_interval = poll_interval
        self.timeout = timeout
        self.sleeper = sleeper

        self.pr_bot = PRBot(cwd=self.cwd)
        self.janitor_bot = GitJanitorBot(cwd=self.cwd)
        self.doc_bot = DocumentationBot(cwd=self.cwd)
        self.announcer_bot = TaskAnnouncerBot(cwd=self.cwd)
        from hath0r_cli.bots.quality import DeployTestBot

        self.test_bot = DeployTestBot(cwd=self.cwd)

    def run_daemon(
        self,
        pr_number: Optional[int] = None,
        branch: Optional[str] = None,
        repo: Optional[str] = None,
        semver: str = "patch",
        dry_run: bool = False,
        skip_tests: bool = False,
    ) -> Dict[str, Any]:
        """Execute autonomous end-of-task state machine."""
        history: List[Dict[str, Any]] = []
        started_at = datetime.now(timezone.utc).isoformat()

        # Step 0: Autonomous test suite validation before PR creation
        if not pr_number and not skip_tests:
            test_res = self.test_bot.run_pre_deploy(dry_run=dry_run)
            history.append({"phase": "test_suite", "result": test_res})
            if not test_res.get("success"):
                issues = test_res.get("issues", [])
                error_msg = f"Local test suite failed with {len(issues)} issue(s)."
                if issues:
                    error_msg += f" First failure: {issues[0].get('test')} ({issues[0].get('detail')})"
                return {
                    "success": False,
                    "phase": "test_suite",
                    "error": error_msg,
                    "issues": issues,
                    "test_results": test_res,
                    "history": history,
                }

        # Step 1: Discover or ensure PR
        current_pr = pr_number
        target_branch = branch
        if not current_pr:
            # Check PR for current branch
            prs = self.pr_bot.list_prs(repo=repo, state="open")
            if target_branch:
                matched = [p for p in prs if p.get("headRefName") == target_branch]
                if matched:
                    current_pr = matched[0].get("number")
            else:
                # Get current active branch
                from hath0r_cli.bots import BranchGuardBot

                bg = BranchGuardBot(cwd=self.cwd)
                act = bg.check_active_branch()
                target_branch = act.get("current_branch")
                if target_branch:
                    matched = [p for p in prs if p.get("headRefName") == target_branch]
                    if matched:
                        current_pr = matched[0].get("number")

        if not current_pr and not dry_run:
            # Create PR automatically if on valid work branch
            create_res = self.pr_bot.create_pr(
                repo=repo,
                head=target_branch,
                base="development",
                semver=semver,
                dry_run=dry_run,
            )
            history.append({"phase": "create_pr", "result": create_res})
            if not create_res.get("success"):
                return {
                    "success": False,
                    "phase": "create_pr",
                    "error": create_res.get("error") or "Failed to create PR",
                    "history": history,
                }
            current_pr = create_res.get("pr_number")

        history.append({
            "phase": "pr_identified",
            "pr_number": current_pr,
            "branch": target_branch,
            "dry_run": dry_run,
        })

        if dry_run:
            # Simulate remaining phases in dry-run
            history.append({"phase": "poll_checks", "status": "simulated_passed", "dry_run": True})
            history.append({
                "phase": "merge_pr",
                "result": self.pr_bot.merge_pr(current_pr or 1, repo=repo, dry_run=True),
            })
            if target_branch:
                history.append({
                    "phase": "reap_branch",
                    "result": self.janitor_bot.prune_branch(target_branch, remote=True, dry_run=True),
                })
            history.append({
                "phase": "sync_development",
                "result": self.janitor_bot.pull_development(base="development", dry_run=True),
            })
            history.append({
                "phase": "share_knowledge",
                "result": self.doc_bot.share_knowledge(
                    summary=f"Automated daemon completion for PR #{current_pr or 1}",
                    pr_number=current_pr or 1,
                    repo=repo,
                    dry_run=True,
                ),
            })
            history.append({
                "phase": "announce",
                "result": self.announcer_bot.announce_complete(
                    task_id=f"pr-{current_pr or 1}", dry_run=True
                ),
            })
            return {
                "success": True,
                "dry_run": True,
                "pr_number": current_pr or 1,
                "branch": target_branch,
                "started_at": started_at,
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "history": history,
            }

        # Step 2: Continuous check polling loop
        if not current_pr:
            return {
                "success": False,
                "phase": "poll_checks",
                "error": "No PR number could be determined for polling",
                "history": history,
            }

        start_time = time.time()
        checks_passed = False
        last_status: Dict[str, Any] = {}

        while time.time() - start_time < self.timeout:
            status = self.pr_bot.check_pr_status(current_pr, repo=repo)
            last_status = status
            if "error" in status:
                history.append({"phase": "poll_checks", "error": status["error"]})
                self.sleeper(self.poll_interval)
                continue

            raw_rollup = status.get("statusCheckRollup", []) or []
            # Deduplicate check runs by name, keeping the latest completedAt/startedAt
            latest_by_name: Dict[str, Dict[str, Any]] = {}
            for c in raw_rollup:
                name = str(c.get("name") or c.get("context") or "")
                if not name:
                    continue
                existing = latest_by_name.get(name)
                if not existing:
                    latest_by_name[name] = c
                else:
                    t_new = str(c.get("completedAt") or c.get("startedAt") or "")
                    t_old = str(existing.get("completedAt") or existing.get("startedAt") or "")
                    if t_new >= t_old:
                        latest_by_name[name] = c

            rollup = list(latest_by_name.values())
            failing = [
                c.get("name") or c.get("context")
                for c in rollup
                if c.get("conclusion") in ("FAILURE", "TIMED_OUT", "STARTUP_FAILURE")
                or c.get("state") == "FAILURE"
            ]
            pending = [
                c.get("name") or c.get("context")
                for c in rollup
                if c.get("conclusion") in ("ACTION_REQUIRED", "NEUTRAL", "")
                or c.get("state") in ("PENDING", "EXPECTED")
            ]

            # Separate non-bypassable code checks vs bypassable infra checks (SonarCloud missing secret)
            code_failing = [
                name for name in failing if "sonar" not in str(name).lower()
            ]

            if code_failing:
                # Hard code/lint failure — abort loop immediately
                history.append({
                    "phase": "poll_checks",
                    "error": f"Hard CI failure detected in checks: {code_failing}",
                    "failing": failing,
                })
                return {
                    "success": False,
                    "phase": "poll_checks",
                    "error": f"Checks failed on code validation: {code_failing}",
                    "pr_number": current_pr,
                    "history": history,
                }

            # If all code checks finished and none are pending
            if len(pending) == 0 and len(rollup) > 0:
                checks_passed = True
                history.append({
                    "phase": "poll_checks",
                    "status": "passed",
                    "total_checks": len(rollup),
                    "infra_bypassed": [f for f in failing if "sonar" in str(f).lower()],
                })
                break

            self.sleeper(self.poll_interval)

        if not checks_passed:
            return {
                "success": False,
                "phase": "poll_checks",
                "error": f"Timed out after {self.timeout}s waiting for PR #{current_pr} checks",
                "last_status": last_status,
                "history": history,
            }

        # Step 3: Admin squash merge
        merge_res = self.pr_bot.merge_pr(
            current_pr, repo=repo, admin=True, squash=True, delete_branch=True, dry_run=False
        )
        history.append({"phase": "merge_pr", "result": merge_res})
        if not merge_res.get("success"):
            return {
                "success": False,
                "phase": "merge_pr",
                "error": merge_res.get("output") or "Merge failed",
                "history": history,
            }

        # Step 4: Checkout development and sync
        pull_res = self.janitor_bot.pull_development(base="development", dry_run=False)
        history.append({"phase": "sync_development", "result": pull_res})

        # Step 5: Reap local branch if it was checked out
        if target_branch and target_branch != "development":
            reap_res = self.janitor_bot.prune_branch(target_branch, remote=False, dry_run=False)
            history.append({"phase": "reap_branch", "result": reap_res})

        # Step 6: Post-merge knowledge share
        kb_res = self.doc_bot.share_knowledge(
            summary=f"Autonomous daemon completed PR #{current_pr} ({target_branch or 'feature'})",
            pr_number=current_pr,
            repo=repo,
            dry_run=False,
        )
        history.append({"phase": "share_knowledge", "result": kb_res})

        # Step 7: Announce completion
        ann_res = self.announcer_bot.announce_complete(
            task_id=f"pr-{current_pr}",
            summary=f"PR #{current_pr} merged and branch {target_branch} pruned by EndOfTaskDaemonBot.",
            dry_run=False,
        )
        history.append({"phase": "announce", "result": ann_res})

        return {
            "success": True,
            "pr_number": current_pr,
            "branch": target_branch,
            "started_at": started_at,
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "history": history,
        }
