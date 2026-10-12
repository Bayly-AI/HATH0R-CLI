"""Orient Command for HATH0R CLI — Repository Architecture & Cognitive Orientation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import click

from hath0r_cli.bots.orient_bot import OrientBot
from hath0r_cli.common import (
    _build_response,
    _emit_response,
    console,
)


@click.command("orient")
@click.option("--repo", "-r", "target_repo", default=None, help="Target specific repository directory path.")
@click.option("--markdown", "-m", "as_markdown", is_flag=True, help="Force Markdown output instead of Rich TUI.")
@click.option("--json", "as_json", is_flag=True, help="Output raw JSON orientation payload matching schema contract.")
@click.pass_context
def orient_cmd(ctx: click.Context, target_repo: Optional[str], as_markdown: bool, as_json: bool) -> None:
    """Execute unified repository orientation across AgentGraph, README, Code AST, Metrics, and Calibration."""
    target_path = Path(target_repo).resolve() if target_repo else Path.cwd().resolve()
    bot = OrientBot(workspace_root=target_path)

    if as_json:
        report = bot.generate_orientation_report(repo_path=target_path)
        click.echo(json.dumps(report, indent=2))
        return

    if as_markdown:
        res = bot.run(repo_path=target_path, render_mode="markdown")
        click.echo(res["output"])
        return

    res = bot.run(repo_path=target_path, render_mode="auto")
    report = res["report"]

    response = _build_response(
        ctx,
        command="orient",
        state="ok" if report.get("verdict", {}).get("status") == "ORIENTED" else "degraded",
        data=report,
    )

    def _text() -> None:
        console.print(res["output"])

    _emit_response(ctx, response, text_renderer=_text)
