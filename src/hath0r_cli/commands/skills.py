"""Skills & Rule-File BITE Supply-Chain Audit Commands (CR-AGENTIC-SEC-001 / WS1)."""

from __future__ import annotations

from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from hath0r_cli.bots.bite_verifier_bot import BITEVerifierBot
from hath0r_cli.common import _build_response, _emit_response

console = Console()


@click.group("skills")
def skills() -> None:
    """Manage and audit agent skills (SKILL.md) and rule files under BITE."""


@skills.command("audit")
@click.option("--dir", "target_dir", type=click.Path(exists=True), default=".", help="Workspace directory to scan.")
@click.pass_context
def skills_audit(ctx: click.Context, target_dir: str) -> None:
    """Audit SKILL.md, AGENTS.md, and WARP.md files under BITE supply-chain verification."""
    bot = BITEVerifierBot(workspace_root=Path(target_dir).resolve())
    res = bot.audit_skills_and_rules(Path(target_dir).resolve())
    state = "ok" if res.get("passed") else "error"
    response = _build_response(ctx, command="skills.audit", state=state, data=res)

    def _text() -> None:
        table = Table(title="BITE Skills & Rules Integrity Audit")
        table.add_column("Path", style="bold cyan")
        table.add_column("Type", style="magenta")
        table.add_column("Verdict", style="bold")
        table.add_column("SHA-256", style="dim")
        table.add_column("Behaviors", justify="right")
        for art in res.get("artifacts", []):
            v = art.get("verdict", "CLEAN")
            color = "green" if v == "CLEAN" else ("yellow" if v == "RISKY" else "red")
            table.add_row(
                str(art.get("path", "")),
                str(art.get("artifact_type", "")),
                f"[{color}]{v}[/{color}]",
                str(art.get("sha256", ""))[:16],
                str(len(art.get("behaviors", []))),
            )
        console.print(table)

    _emit_response(ctx, response, text_renderer=_text)
    if not res.get("passed"):
        ctx.exit(1)
