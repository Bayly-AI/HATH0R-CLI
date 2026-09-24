"""Dynamic bot registry and workflow step dispatcher for Hath0r automation factories."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from hath0r_cli.bots import (
    BranchBot,
    BranchGuardBot,
    DockerBot,
    DocumentationBot,
    GitJanitorBot,
    IssueGuardBot,
    PRBot,
    TaskAnnouncerBot,
)
from hath0r_cli.bots.quality import DeployTestBot, PreflightBot, QualityGateBot, ReleaseBot
from hath0r_cli.factory_manager import FactoryManagerBot


@dataclass
class StepExecutionResult:
    """Result of an individual workflow step execution."""

    bot_id: str
    action: str
    success: bool
    data: Any = None
    error: str | None = None
    dry_run: bool = False
    policy: str = "abort"
    retries: int = 0
    duration_ms: int = 0
    aborted: bool = False

    def to_dict(self) -> dict[str, Any]:
        res: dict[str, Any] = {
            "bot": self.bot_id,
            "action": self.action,
            "success": self.success,
            "policy": self.policy,
            "retries": self.retries,
            "duration_ms": self.duration_ms,
        }
        if self.aborted:
            res["aborted"] = True
        if self.dry_run:
            res["dry_run"] = True
        if self.error is not None:
            res["error"] = self.error
        if self.data is not None:
            res["data"] = self.data
        return res


@dataclass
class WorkflowExecutionResult:
    """Result of an entire workflow execution."""

    workflow_id: str
    name: str
    success: bool
    steps: list[StepExecutionResult] = field(default_factory=list)
    run_id: str = ""
    aborted: bool = False

    def to_dict(self) -> dict[str, Any]:
        res: dict[str, Any] = {
            "id": self.workflow_id,
            "name": self.name,
            "success": self.success,
            "steps": [s.to_dict() for s in self.steps],
        }
        if self.run_id:
            res["run_id"] = self.run_id
        if self.aborted:
            res["aborted"] = True
        return res


class BotRegistry:
    """Registry maintaining active bots and dynamic dispatch mappings."""

    def __init__(self, cwd: Path | None = None) -> None:
        self.cwd = cwd or Path.cwd()
        self._bots: dict[str, Any] = {
            "branch-bot": BranchBot(cwd=self.cwd),
            "branch-guard-bot": BranchGuardBot(cwd=self.cwd),
            "issue-guard-bot": IssueGuardBot(cwd=self.cwd),
            "pr-bot": PRBot(cwd=self.cwd),
            "git-janitor-bot": GitJanitorBot(cwd=self.cwd),
            "documentation-bot": DocumentationBot(cwd=self.cwd),
            "task-announcer-bot": TaskAnnouncerBot(cwd=self.cwd),
            "docker-bot": DockerBot(cwd=self.cwd),
            "docker-monitor-bot": DockerBot(cwd=self.cwd),
            "factory-manager-bot": FactoryManagerBot(cwd=self.cwd),
            "quality-gate-bot": QualityGateBot(cwd=self.cwd),
            "preflight-bot": PreflightBot(cwd=self.cwd),
            "deploy-test-bot": DeployTestBot(cwd=self.cwd),
            "release-bot": ReleaseBot(cwd=self.cwd),
        }

    def get_bot(self, bot_id: str) -> Any | None:
        return self._bots.get(bot_id)

    def registered_bot_ids(self) -> list[str]:
        return list(self._bots.keys())

    def invoke(
        self,
        bot_id: str,
        action: str,
        args: dict[str, Any] | None = None,
        *,
        repo: str | None = None,
        dry_run: bool = False,
        context: dict[str, Any] | None = None,
    ) -> StepExecutionResult:
        """Dynamically dispatch an action call to the specified bot."""
        bot = self.get_bot(bot_id)
        if not bot:
            return StepExecutionResult(
                bot_id=bot_id,
                action=action,
                success=False,
                error=f"Bot '{bot_id}' is not registered in active bot suite.",
                dry_run=dry_run,
            )

        args = dict(args or {})
        ctx = context or {}

        try:
            # Dispatch based on bot type and action name
            if bot_id == "issue-guard-bot":
                return self._dispatch_issue_guard_bot(bot, action, args, repo=repo, dry_run=dry_run, context=ctx)
            elif bot_id == "branch-guard-bot":
                return self._dispatch_branch_guard_bot(bot, action, args, dry_run=dry_run, context=ctx)
            elif bot_id == "pr-bot":
                return self._dispatch_pr_bot(bot, action, args, repo=repo, dry_run=dry_run, context=ctx)
            elif bot_id == "git-janitor-bot":
                return self._dispatch_janitor_bot(bot, action, args, repo=repo, dry_run=dry_run, context=ctx)
            elif bot_id == "branch-bot":
                return self._dispatch_branch_bot(bot, action, args, dry_run=dry_run)
            elif bot_id == "documentation-bot":
                return self._dispatch_doc_bot(bot, action, args, repo=repo, dry_run=dry_run, context=ctx)
            elif bot_id == "task-announcer-bot":
                return self._dispatch_announcer_bot(bot, action, args, dry_run=dry_run, context=ctx)
            elif bot_id in ("docker-bot", "docker-monitor-bot"):
                return self._dispatch_docker_bot(bot, bot_id, action, args, dry_run=dry_run, context=ctx)
            elif bot_id == "factory-manager-bot":
                return self._dispatch_factory_manager(bot, action, args, dry_run=dry_run)
            elif bot_id == "quality-gate-bot":
                return self._dispatch_quality_gate(bot, action, args, repo=repo, dry_run=dry_run, context=ctx)
            elif bot_id == "preflight-bot":
                return self._dispatch_preflight(bot, action, args, dry_run=dry_run)
            elif bot_id == "deploy-test-bot":
                return self._dispatch_deploy_test(bot, action, args, dry_run=dry_run)
            elif bot_id == "release-bot":
                return self._dispatch_release(bot, action, args, repo=repo, dry_run=dry_run)
            else:
                return StepExecutionResult(
                    bot_id=bot_id,
                    action=action,
                    success=False,
                    error=f"No dispatcher implemented for bot '{bot_id}'.",
                    dry_run=dry_run,
                )
        except Exception as exc:
            return StepExecutionResult(
                bot_id=bot_id,
                action=action,
                success=False,
                error=f"Exception during step execution: {exc}",
                dry_run=dry_run,
            )

    def _dispatch_issue_guard_bot(
        self,
        bot: IssueGuardBot,
        action: str,
        args: dict[str, Any],
        repo: str | None,
        dry_run: bool,
        context: dict[str, Any],
    ) -> StepExecutionResult:
        target_repo = args.get("repo") or repo
        if action in ("verify-issue", "verify"):
            issue_num = int(args.get("issue_number") or context.get("issue_number") or 0)
            res = bot.verify_issue(issue_num, repo=target_repo, dry_run=dry_run)
            if res.get("success") and res.get("issue_number"):
                context["issue_number"] = res["issue_number"]
            return StepExecutionResult(
                bot_id="issue-guard-bot",
                action=action,
                success=bool(res.get("success")),
                data=res,
                error=res.get("error"),
                dry_run=dry_run,
            )

        elif action in ("create-issue", "create"):
            title = args.get("title", "")
            body = args.get("body")
            labels = args.get("labels")
            res = bot.create_issue(title, body=body, labels=labels, repo=target_repo, dry_run=dry_run)
            if res.get("issue_number"):
                context["issue_number"] = res["issue_number"]
            return StepExecutionResult(
                bot_id="issue-guard-bot",
                action=action,
                success=bool(res.get("success")),
                data=res,
                error=res.get("error"),
                dry_run=dry_run,
            )

        elif action in ("view-issue", "view"):
            issue_num = int(args.get("issue_number") or context.get("issue_number") or 0)
            res = bot.view_issue(issue_num, repo=target_repo)
            return StepExecutionResult(
                bot_id="issue-guard-bot",
                action=action,
                success=bool(res.get("success")),
                data=res,
                error=res.get("error"),
                dry_run=dry_run,
            )

        return StepExecutionResult(
            bot_id="issue-guard-bot",
            action=action,
            success=False,
            error=f"Unknown action '{action}' for issue-guard-bot.",
            dry_run=dry_run,
        )

    def _dispatch_branch_guard_bot(
        self,
        bot: BranchGuardBot,
        action: str,
        args: dict[str, Any],
        dry_run: bool,
        context: dict[str, Any],
    ) -> StepExecutionResult:
        if action in ("check-active-branch", "check-branch", "check"):
            res = bot.check_active_branch()
            if res.get("current_branch"):
                context["branch"] = res["current_branch"]
            # Fails if blocked on protected canonical branch
            success = bool(res.get("success")) and not bool(res.get("blocked", False))
            return StepExecutionResult(
                bot_id="branch-guard-bot",
                action=action,
                success=success,
                data=res,
                error=res.get("message") if not success else None,
                dry_run=dry_run,
            )

        elif action in ("ensure-work-branch", "ensure-branch", "ensure"):
            issue_num = int(args.get("issue_number") or context.get("issue_number") or 0)
            slug = args.get("slug") or context.get("slug") or "work"
            prefix = args.get("prefix", "feature")
            base = args.get("base", "development")
            res = bot.ensure_work_branch(issue_num, slug, prefix=prefix, base=base, dry_run=dry_run)
            if res.get("branch"):
                context["branch"] = res["branch"]
            return StepExecutionResult(
                bot_id="branch-guard-bot",
                action=action,
                success=bool(res.get("success")),
                data=res,
                error=res.get("error"),
                dry_run=dry_run,
            )

        return StepExecutionResult(
            bot_id="branch-guard-bot",
            action=action,
            success=False,
            error=f"Unknown action '{action}' for branch-guard-bot.",
            dry_run=dry_run,
        )

    def _dispatch_pr_bot(
        self,
        bot: PRBot,
        action: str,
        args: dict[str, Any],
        repo: str | None,
        dry_run: bool,
        context: dict[str, Any],
    ) -> StepExecutionResult:
        target_repo = args.get("repo") or repo
        if action == "list-prs":
            state = args.get("state", "open")
            prs = bot.list_prs(repo=target_repo, state=state)
            context["prs"] = prs
            return StepExecutionResult(
                bot_id="pr-bot", action=action, success=True, data={"prs": prs, "count": len(prs)}
            )

        elif action in ("process-dependabot", "triage-dependabot"):
            auto_merge = args.get("auto_merge", True)
            # If pr_number explicitly provided, process single PR
            if "pr_number" in args:
                res = bot.process_dependabot(
                    int(args["pr_number"]), repo=target_repo, auto_merge=auto_merge, dry_run=dry_run
                )
                return StepExecutionResult(
                    bot_id="pr-bot", action=action, success="error" not in res, data=res, dry_run=dry_run
                )
            else:
                # Process candidate dependabot PRs from prior list-prs or fetch fresh
                raw_prs = context.get("prs")
                pr_list: list[dict[str, Any]] = (
                    raw_prs if isinstance(raw_prs, list) else bot.list_prs(repo=target_repo, state="open")
                )
                dep_prs = [p for p in pr_list if "dependabot" in p.get("author", {}).get("login", "").lower()]
                triage_results = [
                    bot.process_dependabot(dp["number"], repo=target_repo, auto_merge=auto_merge, dry_run=dry_run)
                    for dp in dep_prs
                ]
                return StepExecutionResult(
                    bot_id="pr-bot",
                    action=action,
                    success=True,
                    data={"processed": triage_results, "count": len(triage_results)},
                    dry_run=dry_run,
                )

        elif action == "check-status":
            pr_num = int(args.get("pr_number") or context.get("pr_number") or 0)
            res = bot.check_pr_status(pr_num, repo=target_repo)
            return StepExecutionResult(bot_id="pr-bot", action=action, success="error" not in res, data=res)

        elif action in ("create-pr", "create"):
            title = args.get("title")
            body = args.get("body")
            base = args.get("base", "development")
            head = args.get("head") or context.get("branch")
            draft = bool(args.get("draft", False))
            semver = args.get("semver", "patch")
            res = bot.create_pr(
                title=title,
                body=body,
                base=base,
                head=head,
                repo=target_repo,
                draft=draft,
                semver=semver,
                dry_run=dry_run,
            )
            if res.get("pr_number"):
                context["pr_number"] = res["pr_number"]
            if res.get("branch"):
                context["branch"] = res["branch"]
            return StepExecutionResult(
                bot_id="pr-bot", action=action, success=bool(res.get("success")), data=res, dry_run=dry_run
            )

        elif action in ("monitor-checks", "monitor", "verify-checks"):
            pr_num = int(args.get("pr_number") or context.get("pr_number") or 0)
            res = bot.monitor_checks(pr_num, repo=target_repo, dry_run=dry_run)
            return StepExecutionResult(
                bot_id="pr-bot", action=action, success=bool(res.get("success")), data=res, dry_run=dry_run
            )

        elif action == "merge-pr":
            pr_num = int(args.get("pr_number") or context.get("pr_number") or 0)
            admin = bool(args.get("admin", True))
            squash = bool(args.get("squash", True))
            delete_branch = bool(args.get("delete_branch", True))
            res = bot.merge_pr(
                pr_num,
                repo=target_repo,
                admin=admin,
                squash=squash,
                delete_branch=delete_branch,
                dry_run=dry_run,
            )
            return StepExecutionResult(
                bot_id="pr-bot", action=action, success=bool(res.get("success")), data=res, dry_run=dry_run
            )

        return StepExecutionResult(
            bot_id="pr-bot",
            action=action,
            success=False,
            error=f"Unknown action '{action}' for pr-bot.",
            dry_run=dry_run,
        )

    def _dispatch_janitor_bot(
        self,
        bot: GitJanitorBot,
        action: str,
        args: dict[str, Any],
        repo: str | None,
        dry_run: bool,
        context: dict[str, Any],
    ) -> StepExecutionResult:
        target_repo = args.get("repo") or repo
        if action in ("scan-stale", "scan"):
            scan_res = bot.scan_stale_branches(repo=target_repo)
            context["stale_branches"] = scan_res.get("stale_branches", [])
            return StepExecutionResult(bot_id="git-janitor-bot", action=action, success=True, data=scan_res)

        elif action in ("prune-branches", "prune", "prune-branch"):
            target_branch = args.get("branch") or context.get("branch")
            remote = args.get("remote", True)
            if target_branch:
                p_res = bot.prune_branch(target_branch, remote=remote, dry_run=dry_run)
                return StepExecutionResult(
                    bot_id="git-janitor-bot",
                    action=action,
                    success=bool(p_res.get("success")),
                    data=p_res,
                    dry_run=dry_run,
                )
            else:
                stale = context.get("stale_branches")
                if stale is None:
                    scan_res = bot.scan_stale_branches(repo=target_repo)
                    stale = scan_res.get("stale_branches", [])
                pruned = [
                    {"branch": b["branch"], "result": bot.prune_branch(b["branch"], remote=remote, dry_run=dry_run)}
                    for b in stale
                ]
                return StepExecutionResult(
                    bot_id="git-janitor-bot",
                    action=action,
                    success=True,
                    data={"pruned": pruned, "count": len(pruned)},
                    dry_run=dry_run,
                )

        elif action in ("pull-development", "pull-origin", "sync-development"):
            base = args.get("base", "development")
            res = bot.pull_development(base=base, dry_run=dry_run)
            return StepExecutionResult(
                bot_id="git-janitor-bot",
                action=action,
                success=bool(res.get("success")),
                data=res,
                dry_run=dry_run,
            )

        return StepExecutionResult(
            bot_id="git-janitor-bot",
            action=action,
            success=False,
            error=f"Unknown action '{action}' for git-janitor-bot.",
            dry_run=dry_run,
        )

    def _dispatch_branch_bot(
        self,
        bot: BranchBot,
        action: str,
        args: dict[str, Any],
        dry_run: bool,
    ) -> StepExecutionResult:
        if action in ("validate-name", "validate"):
            name = args.get("name", "")
            res = bot.validate_name(name)
            return StepExecutionResult(bot_id="branch-bot", action=action, success=bool(res.get("valid")), data=res)
        elif action in ("create-branch", "create-work-branch"):
            prefix = args.get("prefix", "feature")
            issue_number = int(args.get("issue_number", 0))
            slug = args.get("slug", "work")
            base = args.get("base", "development")
            res = bot.create_branch(prefix, issue_number, slug, base=base, dry_run=dry_run)
            return StepExecutionResult(
                bot_id="branch-bot",
                action=action,
                success=bool(res.get("success")),
                data=res,
                dry_run=dry_run,
            )

        return StepExecutionResult(
            bot_id="branch-bot",
            action=action,
            success=False,
            error=f"Unknown action '{action}' for branch-bot.",
            dry_run=dry_run,
        )

    def _dispatch_doc_bot(
        self,
        bot: DocumentationBot,
        action: str,
        args: dict[str, Any],
        repo: str | None,
        dry_run: bool,
        context: dict[str, Any],
    ) -> StepExecutionResult:
        if action in ("generate-summary", "summary"):
            ctx_prs = context.get("prs")
            pr_data = args.get("pr_data") or (ctx_prs[0] if isinstance(ctx_prs, list) and ctx_prs else {})
            summary = bot.generate_pr_summary(pr_data)
            context["latest_summary"] = summary
            return StepExecutionResult(
                bot_id="documentation-bot", action=action, success=True, data={"summary": summary}
            )

        elif action in ("sync-wiki", "sync"):
            target_repo = args.get("repo") or repo or "Bayly-AI/HATH0R-CLI"
            title = args.get("title", "PR Documentation")
            content = args.get("content") or context.get("latest_summary", "")
            pr_number = args.get("pr_number") or context.get("pr_number")
            force = bool(args.get("force", False))
            res = bot.sync_to_wiki(
                target_repo,
                title,
                content,
                pr_number=int(pr_number) if pr_number else None,
                dry_run=dry_run,
                force=force,
            )
            return StepExecutionResult(
                bot_id="documentation-bot",
                action=action,
                success=bool(res.get("success", True)),
                data=res,
                dry_run=dry_run,
            )

        elif action in ("share-knowledge", "share"):
            summary_val = args.get("summary") or context.get("latest_summary")
            share_summary: str | None = str(summary_val) if summary_val else None
            notes = args.get("notes")
            target_kb = args.get("target_kb")
            pr_number = args.get("pr_number") or context.get("pr_number")
            res = bot.share_knowledge(
                summary=share_summary,
                notes=notes,
                target_kb=target_kb,
                pr_number=int(pr_number) if pr_number else None,
                repo=args.get("repo") or repo,
                dry_run=dry_run,
            )
            return StepExecutionResult(
                bot_id="documentation-bot",
                action=action,
                success=bool(res.get("success")),
                data=res,
                dry_run=dry_run,
            )

        return StepExecutionResult(
            bot_id="documentation-bot",
            action=action,
            success=False,
            error=f"Unknown action '{action}' for documentation-bot.",
        )

    def _dispatch_announcer_bot(
        self,
        bot: TaskAnnouncerBot,
        action: str,
        args: dict[str, Any],
        dry_run: bool,
        context: dict[str, Any],
    ) -> StepExecutionResult:
        if action in ("announce-complete", "announce"):
            task_id = args.get("task_id") or context.get("task_id") or "end-of-task"
            summary = args.get("summary") or context.get("latest_summary")
            channel = args.get("channel", "console")
            res = bot.announce_complete(task_id=task_id, summary=summary, channel=channel, dry_run=dry_run)
            return StepExecutionResult(
                bot_id="task-announcer-bot",
                action=action,
                success=bool(res.get("success")),
                data=res,
                dry_run=dry_run,
            )

        return StepExecutionResult(
            bot_id="task-announcer-bot",
            action=action,
            success=False,
            error=f"Unknown action '{action}' for task-announcer-bot.",
            dry_run=dry_run,
        )

    def _dispatch_docker_bot(
        self,
        bot: Any,
        bot_id: str,
        action: str,
        args: dict[str, Any],
        *,
        dry_run: bool,
        context: dict[str, Any],
    ) -> StepExecutionResult:
        if action in ("validate-workflow", "validate"):
            wf_data = args.get("workflow") or context.get("docker_workflow") or {}
            res = bot.validate_workflow(wf_data)
            return StepExecutionResult(
                bot_id=bot_id,
                action=action,
                success=res.get("valid", False),
                data=res,
                error=None if res.get("valid") else "; ".join(res.get("errors", [])),
                dry_run=dry_run,
            )

        elif action in ("build-container", "build"):
            compose_file = args.get("compose_file") or args.get("file")
            service = args.get("service")
            res = bot.build_container(compose_file=compose_file, service=service, dry_run=dry_run)
            return StepExecutionResult(
                bot_id=bot_id,
                action=action,
                success=res.get("success", False),
                data=res,
                error=res.get("error"),
                dry_run=dry_run,
            )

        elif action in ("up", "start"):
            compose_file = args.get("compose_file") or args.get("file")
            services = args.get("services")
            detach = args.get("detach", True)
            res = bot.up(compose_file=compose_file, services=services, detach=detach, dry_run=dry_run)
            return StepExecutionResult(
                bot_id=bot_id,
                action=action,
                success=res.get("success", False),
                data=res,
                error=res.get("error"),
                dry_run=dry_run,
            )

        elif action in ("healthcheck", "probe"):
            endpoint = args.get("endpoint")
            container_name = args.get("container") or args.get("container_name")
            res = bot.healthcheck(endpoint=endpoint, container_name=container_name, dry_run=dry_run)
            return StepExecutionResult(
                bot_id=bot_id,
                action=action,
                success=res.get("success", False),
                data=res,
                error=res.get("error"),
                dry_run=dry_run,
            )

        elif action in ("diagnose", "diagnose-container"):
            container_name = args.get("container") or args.get("container_name")
            compose_file = args.get("compose_file")
            res = bot.diagnose(container_name=container_name, compose_file=compose_file, dry_run=dry_run)
            return StepExecutionResult(
                bot_id=bot_id,
                action=action,
                success=res.get("success", False),
                data=res,
                error=res.get("error"),
                dry_run=dry_run,
            )

        elif action in ("down", "stop"):
            compose_file = args.get("compose_file") or args.get("file")
            res = bot.down(compose_file=compose_file, dry_run=dry_run)
            return StepExecutionResult(
                bot_id=bot_id,
                action=action,
                success=res.get("success", False),
                data=res,
                error=res.get("error"),
                dry_run=dry_run,
            )

        return StepExecutionResult(
            bot_id=bot_id,
            action=action,
            success=False,
            error=f"Unknown action '{action}' for {bot_id}.",
            dry_run=dry_run,
        )

    def _dispatch_factory_manager(
        self,
        bot: FactoryManagerBot,
        action: str,
        args: dict[str, Any],
        dry_run: bool,
    ) -> StepExecutionResult:
        if action in ("validate", "validate-factory"):
            factory_id = args.get("factory_id")
            res = bot.validate(factory_id)
            return StepExecutionResult(
                bot_id="factory-manager-bot",
                action=action,
                success=bool(res.get("success")),
                data=res,
                error=res.get("error"),
                dry_run=dry_run,
            )
        if action == "list":
            items = bot.list_factories()
            return StepExecutionResult(
                bot_id="factory-manager-bot",
                action=action,
                success=True,
                data={"factories": items, "count": len(items)},
            )
        if action == "create":
            res = bot.create(
                str(args.get("factory_id") or ""),
                name=args.get("name"),
                description=args.get("description") or "",
                dry_run=dry_run,
                force=bool(args.get("force", False)),
            )
            return StepExecutionResult(
                bot_id="factory-manager-bot",
                action=action,
                success=bool(res.get("success")),
                data=res,
                error=res.get("error"),
                dry_run=dry_run,
            )
        if action in ("update", "edit"):
            res = bot.update(
                str(args.get("factory_id") or ""),
                name=args.get("name"),
                description=args.get("description"),
                version=args.get("version"),
                dry_run=dry_run,
            )
            return StepExecutionResult(
                bot_id="factory-manager-bot",
                action=action,
                success=bool(res.get("success")),
                data=res,
                error=res.get("error"),
                dry_run=dry_run,
            )
        if action == "delete":
            res = bot.delete(str(args.get("factory_id") or ""), dry_run=dry_run)
            return StepExecutionResult(
                bot_id="factory-manager-bot",
                action=action,
                success=bool(res.get("success")),
                data=res,
                error=res.get("error"),
                dry_run=dry_run,
            )
        return StepExecutionResult(
            bot_id="factory-manager-bot",
            action=action,
            success=False,
            error=f"Unknown action '{action}' for factory-manager-bot.",
            dry_run=dry_run,
        )

    def _dispatch_quality_gate(
        self,
        bot: QualityGateBot,
        action: str,
        args: dict[str, Any],
        repo: str | None,
        dry_run: bool,
        context: dict[str, Any],
    ) -> StepExecutionResult:
        if action in ("check-pr", "evaluate", "aggregate"):
            pr_num = int(args.get("pr_number") or context.get("pr_number") or 0)
            res = bot.check_pr(pr_num, repo=args.get("repo") or repo, dry_run=dry_run)
            return StepExecutionResult(
                bot_id="quality-gate-bot",
                action=action,
                success=bool(res.get("success")),
                data=res,
                error=res.get("error") or (None if res.get("success") else res.get("message")),
                dry_run=dry_run,
            )
        if action == "evaluate-rollup":
            res = bot.evaluate_rollup(args.get("status_checks") or [])
            return StepExecutionResult(
                bot_id="quality-gate-bot",
                action=action,
                success=bool(res.get("success")),
                data=res,
                dry_run=dry_run,
            )
        return StepExecutionResult(
            bot_id="quality-gate-bot",
            action=action,
            success=False,
            error=f"Unknown action '{action}' for quality-gate-bot.",
            dry_run=dry_run,
        )

    def _dispatch_preflight(
        self,
        bot: PreflightBot,
        action: str,
        args: dict[str, Any],
        dry_run: bool,
    ) -> StepExecutionResult:
        if action in ("run", "preflight", "check"):
            res = bot.run(
                skip_tests=bool(args.get("skip_tests", False)),
                dry_run=dry_run,
            )
            return StepExecutionResult(
                bot_id="preflight-bot",
                action=action,
                success=bool(res.get("success")),
                data=res,
                error=None if res.get("success") else res.get("message"),
                dry_run=dry_run,
            )
        return StepExecutionResult(
            bot_id="preflight-bot",
            action=action,
            success=False,
            error=f"Unknown action '{action}' for preflight-bot.",
            dry_run=dry_run,
        )

    def _dispatch_deploy_test(
        self,
        bot: DeployTestBot,
        action: str,
        args: dict[str, Any],
        dry_run: bool,
    ) -> StepExecutionResult:
        if action in ("pre-deploy", "run-pre-deploy"):
            res = bot.run_pre_deploy(dry_run=dry_run)
        elif action in ("post-deploy", "run-post-deploy"):
            res = bot.run_post_deploy(base_url=args.get("base_url"), dry_run=dry_run)
        else:
            return StepExecutionResult(
                bot_id="deploy-test-bot",
                action=action,
                success=False,
                error=f"Unknown action '{action}' for deploy-test-bot.",
                dry_run=dry_run,
            )
        return StepExecutionResult(
            bot_id="deploy-test-bot",
            action=action,
            success=bool(res.get("success")),
            data=res,
            error=None if res.get("success") else res.get("message"),
            dry_run=dry_run,
        )

    def _dispatch_release(
        self,
        bot: ReleaseBot,
        action: str,
        args: dict[str, Any],
        repo: str | None,
        dry_run: bool,
    ) -> StepExecutionResult:
        if action in ("validate", "validate-version"):
            res = bot.validate()
        elif action in ("notes", "generate-notes"):
            res = bot.generate_notes(version=args.get("version"))
        elif action in ("tag-release", "release", "publish"):
            res = bot.tag_and_release(
                repo=args.get("repo") or repo,
                dry_run=dry_run,
                skip_github_release=bool(args.get("skip_github_release", False)),
            )
        else:
            return StepExecutionResult(
                bot_id="release-bot",
                action=action,
                success=False,
                error=f"Unknown action '{action}' for release-bot.",
                dry_run=dry_run,
            )
        return StepExecutionResult(
            bot_id="release-bot",
            action=action,
            success=bool(res.get("success")),
            data=res,
            error=res.get("error") or (None if res.get("success") else res.get("message")),
            dry_run=dry_run,
        )


def execute_workflow(
    workflow_def: dict[str, Any],
    registry: BotRegistry,
    *,
    repo: str | None = None,
    dry_run: bool = False,
    run_id: str | None = None,
) -> WorkflowExecutionResult:
    """Execute all declarative steps inside a workflow, honoring on_failure policies."""
    wf_id = workflow_def.get("id", "unnamed-workflow")
    name = workflow_def.get("name", wf_id)
    steps = workflow_def.get("steps", [])
    active_run_id = run_id or f"run_{uuid.uuid4().hex[:12]}"

    results: list[StepExecutionResult] = []
    context: dict[str, Any] = {}
    all_success = True
    aborted = False

    for step in steps:
        if not isinstance(step, dict):
            continue
        bot_id = str(step.get("bot", ""))
        action = str(step.get("action", ""))
        args = step.get("args") if isinstance(step.get("args"), dict) else {}
        on_failure = str(step.get("on_failure", "abort")).lower()
        if on_failure not in {"continue", "abort", "retry"}:
            on_failure = "abort"
        max_retries = int(step.get("retry_count", 2)) if on_failure == "retry" else 0

        t0 = time.perf_counter()
        attempt = 0
        step_res: StepExecutionResult | None = None

        while True:
            attempt += 1
            step_res = registry.invoke(
                bot_id=bot_id,
                action=action,
                args=args,
                repo=repo,
                dry_run=dry_run,
                context=context,
            )
            if step_res.success or attempt > max_retries:
                break

        duration_ms = max(0, int((time.perf_counter() - t0) * 1000))
        step_res.duration_ms = duration_ms
        step_res.policy = on_failure
        step_res.retries = attempt - 1

        results.append(step_res)

        if not step_res.success:
            if on_failure == "abort":
                all_success = False
                aborted = True
                step_res.aborted = True
                break
            elif on_failure == "continue":
                # continue logs finding/error but workflow continues
                all_success = False
            else:  # retry exhausted
                all_success = False
                aborted = True
                step_res.aborted = True
                break

    return WorkflowExecutionResult(
        workflow_id=wf_id,
        name=name,
        success=all_success,
        steps=results,
        run_id=active_run_id,
        aborted=aborted,
    )


def spool_telemetry_event(
    event_type: str,
    payload: dict[str, Any],
    *,
    base_dir: Path | None = None,
) -> Path | None:
    """Spool a telemetry event in append-only JSONL format to .hath0r/spool/.

    Per ADR-004 and HATH0R telemetry guidelines, telemetry never blocks or fails primary execution.
    """
    import json
    import os
    from datetime import datetime, timezone

    try:
        # Determine spool dir
        spool_dir: Path
        if base_dir:
            spool_dir = base_dir / ".hath0r" / "spool"
        else:
            group_root_env = os.environ.get("HATH0R_GROUP_ROOT")
            if group_root_env and Path(group_root_env).is_dir():
                spool_dir = Path(group_root_env) / ".hath0r" / "spool"
            else:
                spool_dir = Path.cwd() / ".hath0r" / "spool"

        spool_dir.mkdir(parents=True, exist_ok=True)
        today = datetime.now(timezone.utc).strftime("%Y%m%d")
        spool_file = spool_dir / f"telemetry-{today}.jsonl"

        event = {
            "schema": "hath0r.telemetry.event/1",
            "event_id": f"evt_{uuid.uuid4().hex[:12]}",
            "event_type": event_type,
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "payload": payload,
        }

        with spool_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, separators=(",", ":")) + "\n")

        return spool_file
    except Exception:
        # Telemetry is strictly never-fatal per AEG-REQ-TEL-002
        return None
