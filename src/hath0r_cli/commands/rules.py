"""Canonical rule rollout commands for HATH0R CLI (#528)."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import click
from rich.table import Table

from hath0r_cli.bots.rule_rollout_bot import RuleRolloutBot
from hath0r_cli.common import _build_response, _emit_response, console

_ROOT_HELP = "Root workspace directory to scan (defaults to /Users/raybayly/Development)."


@click.group("rules")
def rules_cmd() -> None:
    """Canonical CR-* rule coverage and cross-repo rollout (AGENTS.md, SemVer bump, issue, PR)."""


def _repo_table(title: str, repos: list) -> Table:
    table = Table(title=title)
    table.add_column("Repository", style="bold cyan")
    table.add_column("Remote")
    table.add_column("Status", justify="center")
    table.add_column("Version", justify="right")
    table.add_column("PR / Error")
    for r in repos:
        version = f"{r.get('old_version') or '—'} → {r['new_version']}" if r.get("new_version") else ""
        table.add_row(r["repo"], r.get("slug") or "—", r["status"], version, r.get("pr") or r.get("error") or "")
    return table


@rules_cmd.command("list")
@click.pass_context
def rules_list(ctx: click.Context) -> None:
    """List canonical rule sections shipped with the CLI."""
    rules = RuleRolloutBot.list_rules()
    response = _build_response(ctx, command="rules.list", state="ok", data={"rules": rules})

    def _text() -> None:
        for r in rules:
            console.print(f"[bold cyan]{r['rule_id']}[/bold cyan]  {r['title']}")

    _emit_response(ctx, response, text_renderer=_text)


@rules_cmd.command("status")
@click.option("--rule", "rule_id", required=True, help="Rule id, e.g. CR-CLI-ENTRY-001.")
@click.option("--root", "root_dir", default=None, help=_ROOT_HELP)
@click.pass_context
def rules_status(ctx: click.Context, rule_id: str, root_dir: Optional[str]) -> None:
    """Report per-remote coverage of a rule on origin/development."""
    res = RuleRolloutBot(cwd=Path.cwd()).status(rule_id, root_dir)
    response = _build_response(ctx, command="rules.status", state="ok", data=res)

    def _text() -> None:
        console.print(_repo_table(f"{rule_id} coverage ({res['root_dir']})", res["repos"]))
        console.print(", ".join(f"{k}: {v}" for k, v in sorted(res["counts"].items())))

    _emit_response(ctx, response, text_renderer=_text)


@rules_cmd.command("ensure-all")
@click.option("--rule", "rule_id", required=True, help="Rule id, e.g. CR-CLI-ENTRY-001.")
@click.option("--root", "root_dir", default=None, help=_ROOT_HELP)
@click.option(
    "--section-file",
    type=click.Path(exists=True, dir_okay=False),
    default=None,
    help="Markdown section for a rule not shipped with the CLI (must contain '## <RULE-ID>').",
)
@click.option("--apply", is_flag=True, default=False, help="Commit the rule in scratch worktrees (no push).")
@click.option("--publish", is_flag=True, default=False, help="Apply, then open an issue and PR per remote.")
@click.option("--work-dir", default=None, help="Directory for scratch worktrees (defaults to a temp dir).")
@click.option("--keep-worktrees", is_flag=True, default=False, help="Leave worktrees in place for review.")
@click.pass_context
def rules_ensure_all(
    ctx: click.Context,
    rule_id: str,
    root_dir: Optional[str],
    section_file: Optional[str],
    apply: bool,
    publish: bool,
    work_dir: Optional[str],
    keep_worktrees: bool,
) -> None:
    """Roll a canonical rule out to every repository missing it (preview unless --apply/--publish)."""
    res = RuleRolloutBot(cwd=Path.cwd()).ensure_all(
        rule_id,
        root=root_dir,
        section_file=section_file,
        apply=apply,
        publish=publish,
        work_dir=work_dir,
        keep_worktrees=keep_worktrees,
    )
    state = "ok" if res.get("success") else "error"
    response = _build_response(ctx, command="rules.ensure_all", state=state, dry_run=not (apply or publish), data=res)

    def _text() -> None:
        if res.get("error"):
            console.print(f"[bold red]✗ {res['error']}[/bold red]")
            return
        console.print(_repo_table(f"{rule_id} rollout — {res['mode']} ({res['root_dir']})", res["repos"]))
        console.print(", ".join(f"{k}: {v}" for k, v in sorted(res["counts"].items())))
        if res.get("work_dir"):
            console.print(f"Worktrees: {res['work_dir']}")

    _emit_response(ctx, response, text_renderer=_text)
    if not res.get("success"):
        ctx.exit(1)
