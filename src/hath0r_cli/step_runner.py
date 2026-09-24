"""Dynamic bot registry and workflow step dispatcher for Hath0r automation factories."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from hath0r_cli.bots import BranchBot, DocumentationBot, GitJanitorBot, PRBot


@dataclass
class StepExecutionResult:
    """Result of an individual workflow step execution."""

    bot_id: str
    action: str
    success: bool
    data: Any = None
    error: str | None = None
    dry_run: bool = False

    def to_dict(self) -> dict[str, Any]:
        res: dict[str, Any] = {
            "bot": self.bot_id,
            "action": self.action,
            "success": self.success,
        }
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

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.workflow_id,
            "name": self.name,
            "success": self.success,
            "steps": [s.to_dict() for s in self.steps],
        }


class BotRegistry:
    """Registry maintaining active bots and dynamic dispatch mappings."""

    def __init__(self, cwd: Path | None = None) -> None:
        self.cwd = cwd or Path.cwd()
        self._bots: dict[str, Any] = {
            "branch-bot": BranchBot(cwd=self.cwd),
            "pr-bot": PRBot(cwd=self.cwd),
            "git-janitor-bot": GitJanitorBot(cwd=self.cwd),
            "documentation-bot": DocumentationBot(cwd=self.cwd),
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
            if bot_id == "pr-bot":
                return self._dispatch_pr_bot(bot, action, args, repo=repo, dry_run=dry_run, context=ctx)
            elif bot_id == "git-janitor-bot":
                return self._dispatch_janitor_bot(bot, action, args, repo=repo, dry_run=dry_run, context=ctx)
            elif bot_id == "branch-bot":
                return self._dispatch_branch_bot(bot, action, args, dry_run=dry_run)
            elif bot_id == "documentation-bot":
                return self._dispatch_doc_bot(bot, action, args, repo=repo, context=ctx)
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
                prs = context.get("prs")
                if prs is None:
                    prs = bot.list_prs(repo=target_repo, state="open")
                dep_prs = [p for p in prs if "dependabot" in p.get("author", {}).get("login", "").lower()]
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
            pr_num = int(args["pr_number"])
            res = bot.check_pr_status(pr_num, repo=target_repo)
            return StepExecutionResult(bot_id="pr-bot", action=action, success="error" not in res, data=res)

        elif action == "merge-pr":
            pr_num = int(args["pr_number"])
            admin = bool(args.get("admin", False))
            res = bot.merge_pr(pr_num, repo=target_repo, admin=admin, dry_run=dry_run)
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

        elif action in ("prune-branches", "prune"):
            target_branch = args.get("branch")
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
        context: dict[str, Any],
    ) -> StepExecutionResult:
        if action in ("generate-summary", "summary"):
            pr_data = args.get("pr_data") or (context.get("prs")[0] if context.get("prs") else {})
            summary = bot.generate_pr_summary(pr_data)
            context["latest_summary"] = summary
            return StepExecutionResult(
                bot_id="documentation-bot", action=action, success=True, data={"summary": summary}
            )

        elif action in ("sync-wiki", "sync"):
            target_repo = args.get("repo") or repo or "Bayly-AI/HATH0R-CLI"
            title = args.get("title", "PR Documentation")
            content = args.get("content") or context.get("latest_summary", "")
            res = bot.sync_to_wiki(target_repo, title, content)
            return StepExecutionResult(bot_id="documentation-bot", action=action, success=True, data=res)

        return StepExecutionResult(
            bot_id="documentation-bot",
            action=action,
            success=False,
            error=f"Unknown action '{action}' for documentation-bot.",
        )


def execute_workflow(
    workflow_def: dict[str, Any],
    registry: BotRegistry,
    *,
    repo: str | None = None,
    dry_run: bool = False,
) -> WorkflowExecutionResult:
    """Execute all declarative steps inside a workflow."""
    wf_id = workflow_def.get("id", "unnamed-workflow")
    name = workflow_def.get("name", wf_id)
    steps = workflow_def.get("steps", [])

    results: list[StepExecutionResult] = []
    context: dict[str, Any] = {}
    all_success = True

    for step in steps:
        if not isinstance(step, dict):
            continue
        bot_id = str(step.get("bot", ""))
        action = str(step.get("action", ""))
        args = step.get("args") if isinstance(step.get("args"), dict) else {}

        step_res = registry.invoke(
            bot_id=bot_id,
            action=action,
            args=args,
            repo=repo,
            dry_run=dry_run,
            context=context,
        )
        results.append(step_res)
        if not step_res.success:
            all_success = False

    return WorkflowExecutionResult(
        workflow_id=wf_id,
        name=name,
        success=all_success,
        steps=results,
    )
