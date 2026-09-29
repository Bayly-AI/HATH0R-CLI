"""Context command for HATH0R CLI."""

from __future__ import annotations

import click

from hath0r_cli.common import (
    _build_response,
    _emit_response,
    console,
)


@click.group()
def context() -> None:
    """Manage Hyper Context agentic architecture."""
    pass


@context.command("spread")
@click.option("--target", required=True, help="Target directory for hyper context (e.g. src/hath0r_cli/bots)")
@click.option("--feature-name", required=True, help="Human-readable name of the feature (e.g. 'Bots Subsystem')")
@click.pass_context
def context_spread(ctx: click.Context, target: str, feature_name: str) -> None:
    """Spread localized AGENTS.md, rules.md, and canonical.md to a sub-folder."""
    from hath0r_cli.bots.hyper_context import HyperContextBot

    bot = HyperContextBot()
    res = bot.spread_context(target, feature_name)

    response = _build_response(
        ctx,
        command="context.spread",
        state="ok" if res.get("success") else "error",
        data=res,
    )

    def _text() -> None:
        if res.get("success"):
            console.print(f"[bold green]✓ {res['message']}[/bold green]")
            for f in res.get("files_created", []):
                console.print(f"  • {f}")
        else:
            console.print(f"[bold red]✗ Failed to spread context:[/bold red] {res.get('error')}")

    _emit_response(ctx, response, text_renderer=_text)




