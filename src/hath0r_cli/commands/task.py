"""Task command for HATH0R CLI."""

from __future__ import annotations

from pathlib import Path

import click

from hath0r_cli.common import (
    _build_response,
    _cli_repo_root,
    _discover_group_root,
    _emit_response,
)
from hath0r_cli.envelope import Diagnostic


@click.group()
def task() -> None:
    """Task Lifecycle: run canonical start and end-of-task automation and transitions."""


@task.command("start")
@click.option("--issue", "issue_number", default=None, type=int, help="Existing GitHub issue number.")
@click.option("--title", default=None, help="Issue title if creating a new ticket.")
@click.option("--slug", default=None, help="Short slug for branch name (<prefix>/<issue>-<slug>).")
@click.option(
    "--prefix",
    default="feature",
    type=click.Choice(["feature", "bugfix", "hotfix", "enhancement", "research", "fix", "chore"]),
    help="Branch taxonomy prefix.",
)
@click.option("--base", default="development", help="Base branch to branch off of.")
@click.option("--repo", default=None, help="Target GitHub repository (owner/repo).")
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Simulate issue creation/verification and branch checkout.",
)
@click.pass_context
def task_start(
    ctx: click.Context,
    issue_number: int | None,
    title: str | None,
    slug: str | None,
    prefix: str,
    base: str,
    repo: str | None,
    dry_run: bool,
) -> None:
    """Execute canonical start-of-task factory: enforce issue attachment & compliant work branch."""
    import uuid

    import yaml

    from hath0r_cli.step_runner import BotRegistry, execute_workflow, spool_telemetry_event

    cli_repo_root = _cli_repo_root()
    factory_file = cli_repo_root / "cfg" / "factories" / "start-of-task-factory.yaml"
    if not factory_file.is_file():
        response = _build_response(
            ctx,
            command="task.start",
            state="error",
            dry_run=dry_run,
            diagnostics=[
                Diagnostic(
                    severity="error",
                    code="FACTORY_NOT_FOUND",
                    message="Canonical start-of-task-factory.yaml manifest not found.",
                )
            ],
        )
        _emit_response(ctx, response)
        ctx.exit(1)

    # If no issue number provided but title is given, create issue first
    if not issue_number and not title:
        response = _build_response(
            ctx,
            command="task.start",
            state="error",
            dry_run=dry_run,
            diagnostics=[
                Diagnostic(
                    severity="error",
                    code="ISSUE_REQUIRED",
                    message="Either an existing --issue <number> or a new --title <string> is required.",
                )
            ],
        )
        _emit_response(ctx, response)
        ctx.exit(1)

    factory_data = yaml.safe_load(factory_file.read_text(encoding="utf-8"))
    workflow_def = factory_data.get("workflows", [{}])[0]

    # Customize step args based on CLI flags
    clean_slug = (slug or title or "task").lower()
    clean_slug = "".join(c if c.isalnum() else "-" for c in clean_slug).strip("-")[:30]

    steps = []
    if not issue_number and title:
        # Step 1: create issue
        steps.append(
            {
                "bot": "issue-guard-bot",
                "action": "create-issue",
                "args": {"title": title, "repo": repo},
                "on_failure": "abort",
            }
        )
    else:
        # Step 1: verify issue
        steps.append(
            {
                "bot": "issue-guard-bot",
                "action": "verify-issue",
                "args": {"issue_number": issue_number, "repo": repo},
                "on_failure": "abort",
            }
        )
        # Step 2: run issue-factory validation & dependency checking
        steps.append(
            {
                "bot": "issue-manager-bot",
                "action": "validate-issue",
                "args": {"issue_number": issue_number, "repo": repo},
                "on_failure": "warn",
            }
        )

    # Step 3: ensure work branch
    steps.append(
        {
            "bot": "branch-guard-bot",
            "action": "ensure-work-branch",
            "args": {
                "issue_number": issue_number,
                "slug": clean_slug,
                "prefix": prefix,
                "base": base,
            },
            "on_failure": "abort",
        }
    )

    dynamic_wf = {
        "id": workflow_def.get("id", "start-of-task"),
        "name": workflow_def.get("name", "Canonical Start of Task Lifecycle"),
        "steps": steps,
    }

    registry = BotRegistry(cwd=Path.cwd())
    run_id = f"run_{uuid.uuid4().hex[:12]}"

    exec_res = execute_workflow(dynamic_wf, registry, repo=repo, dry_run=dry_run, run_id=run_id)
    all_success = exec_res.success
    state = "ok" if all_success else "error"

    diagnostics = []
    for st in exec_res.steps:
        if not st.success:
            diagnostics.append(
                Diagnostic(
                    code="STEP_EXECUTION_FAILED",
                    message=f"[start-of-task::{st.bot_id}] {st.error or 'Step execution failed'}",
                    severity="error",
                    provenance={"component": "hath0r-cli", "operation": "task.start"},
                )
            )

    spool_telemetry_event(
        event_type="task.start",
        payload={
            "run_id": run_id,
            "state": state,
            "dry_run": dry_run,
            "steps": [s.to_dict() for s in exec_res.steps],
        },
        base_dir=_discover_group_root(),
    )

    response = _build_response(
        ctx,
        command="task.start",
        state=state,
        dry_run=dry_run,
        data={
            "run_id": run_id,
            "workflow": exec_res.to_dict(),
        },
        diagnostics=diagnostics,
    )

    def _text() -> None:
        prefix_str = "[DRY-RUN] " if dry_run else ""
        click.echo(f"{prefix_str}Completed Start of Task workflow ({'SUCCESS' if all_success else 'FAILED'}):")
        for st in exec_res.steps:
            icon = "✓" if st.success else "✗"
            detail = st.data if st.success else st.error
            click.echo(f"  {icon} [{st.bot_id}] {st.action}: {detail}")

    _emit_response(ctx, response, text_renderer=_text)
    if not all_success:
        ctx.exit(1)


@task.command("finish")
@click.option("--repo", default=None, help="Target GitHub repository (owner/repo).")
@click.option("--dry-run", is_flag=True, default=False, help="Simulate PR creation, checks, merge, and branch pruning.")
@click.option(
    "--semver",
    default="patch",
    type=click.Choice(["major", "minor", "patch", "none"]),
    help="SemVer impact.",
)
@click.option(
    "--bot",
    "--watch",
    "bot_mode",
    is_flag=True,
    default=False,
    help="Autonomous bot mode: continuously watch PR checks, merge, and reap branches.",
)
@click.option(
    "--poll-interval",
    default=10.0,
    type=float,
    help="Polling interval in seconds for bot checks.",
)
@click.option(
    "--timeout",
    default=600.0,
    type=float,
    help="Timeout in seconds for bot checks completion.",
)
@click.option(
    "--pr",
    "pr_number",
    type=int,
    default=None,
    help="Target PR number for finish or bot watch.",
)
@click.option(
    "--skip-tests",
    is_flag=True,
    default=False,
    help="Skip autonomous test suite pre-validation.",
)
@click.pass_context
def task_finish(
    ctx: click.Context,
    repo: str | None,
    dry_run: bool,
    semver: str,
    bot_mode: bool,
    poll_interval: float,
    timeout: float,
    pr_number: int | None,
    skip_tests: bool,
) -> None:
    """Execute canonical end-of-task factory before completing an assignment."""
    import uuid

    import yaml

    from hath0r_cli.step_runner import BotRegistry, execute_workflow, spool_telemetry_event

    registry = BotRegistry(cwd=Path.cwd())
    run_id = f"run_{uuid.uuid4().hex[:12]}"

    if bot_mode:
        from hath0r_cli.bots import EndOfTaskBot

        bot_worker = EndOfTaskBot(cwd=Path.cwd(), poll_interval=poll_interval, timeout=timeout)
        bot_res = bot_worker.run_bot(
            pr_number=pr_number,
            repo=repo,
            semver=semver,
            dry_run=dry_run,
            skip_tests=skip_tests,
        )
        all_success = bool(bot_res.get("success"))
        state = "ok" if all_success else "error"
        diagnostics = []
        if not all_success:
            diagnostics.append(
                Diagnostic(
                    code="BOT_EXECUTION_FAILED",
                    message=f"[end-of-task::bot] {bot_res.get('error') or 'Bot cycle failed'}",
                    severity="error",
                    provenance={"component": "hath0r-cli", "operation": "task.finish"},
                )
            )
        spool_telemetry_event(
            event_type="task.finish.bot",
            payload={
                "run_id": run_id,
                "state": state,
                "dry_run": dry_run,
                "bot": bot_res,
            },
            base_dir=_discover_group_root(),
        )
        response = _build_response(
            ctx,
            command="task.finish",
            state=state,
            dry_run=dry_run,
            data={
                "run_id": run_id,
                "bot": bot_res,
            },
            diagnostics=diagnostics,
        )

        def _bot_text() -> None:
            prefix = "[DRY-RUN] " if dry_run else ""
            status_str = "SUCCESS" if all_success else "FAILED"
            click.echo(f"{prefix}Completed Autonomous End of Task Bot ({status_str}):")
            for h in bot_res.get("history", []):
                p = h.get("phase")
                detail = h.get("status") or h.get("result") or h.get("error") or h.get("pr_number")
                click.echo(f"  • [{p}]: {detail}")

        _emit_response(ctx, response, text_renderer=_bot_text)
        if not all_success:
            ctx.exit(1)
        return

    cli_repo_root = _cli_repo_root()
    factory_file = cli_repo_root / "cfg" / "factories" / "end-of-task-factory.yaml"
    if not factory_file.is_file():
        response = _build_response(
            ctx,
            command="task.finish",
            state="error",
            dry_run=dry_run,
            diagnostics=[
                Diagnostic(
                    severity="error",
                    code="FACTORY_NOT_FOUND",
                    message="Canonical end-of-task-factory.yaml manifest not found.",
                )
            ],
        )
        _emit_response(ctx, response)
        ctx.exit(1)

    factory_data = yaml.safe_load(factory_file.read_text(encoding="utf-8"))
    workflow_def = factory_data.get("workflows", [{}])[0]

    exec_res = execute_workflow(workflow_def, registry, repo=repo, dry_run=dry_run, run_id=run_id)
    all_success = exec_res.success
    state = "ok" if all_success else "error"

    diagnostics = []
    for st in exec_res.steps:
        if not st.success:
            diagnostics.append(
                Diagnostic(
                    code="STEP_EXECUTION_FAILED",
                    message=f"[end-of-task::{st.bot_id}] {st.error or 'Step execution failed'}",
                    severity="error",
                    provenance={"component": "hath0r-cli", "operation": "task.finish"},
                )
            )

    spool_telemetry_event(
        event_type="task.finish",
        payload={
            "run_id": run_id,
            "state": state,
            "dry_run": dry_run,
            "steps": [s.to_dict() for s in exec_res.steps],
        },
        base_dir=_discover_group_root(),
    )

    response = _build_response(
        ctx,
        command="task.finish",
        state=state,
        dry_run=dry_run,
        data={
            "run_id": run_id,
            "workflow": exec_res.to_dict(),
        },
        diagnostics=diagnostics,
    )

    def _text() -> None:
        prefix = "[DRY-RUN] " if dry_run else ""
        click.echo(f"{prefix}Completed End of Task workflow ({'SUCCESS' if all_success else 'FAILED'}):")
        for st in exec_res.steps:
            icon = "✓" if st.success else "✗"
            detail = st.data if st.success else st.error
            click.echo(f"  {icon} [{st.bot_id}] {st.action}: {detail}")

    _emit_response(ctx, response, text_renderer=_text)
    if not all_success:
        ctx.exit(1)



