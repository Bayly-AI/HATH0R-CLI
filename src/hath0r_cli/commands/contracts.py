"""Contracts command for HATH0R CLI."""

from __future__ import annotations

from pathlib import Path

import click
from rich.table import Table

from hath0r_cli.common import (
    _build_response,
    _emit_response,
    console,
)


@click.group()
def contracts() -> None:
    """Validate and synchronize JSON schema contracts across member repositories."""
    pass


@contracts.command("validate")
@click.option("--target-dir", default=None, help="Target repository directory to validate contracts for.")
@click.option("--canonical-dir", default=None, help="Canonical contracts directory to compare against.")
@click.pass_context
def contracts_validate(ctx: click.Context, target_dir: str | None, canonical_dir: str | None) -> None:
    """Validate repository schema contracts against canonical definitions."""
    from hath0r_cli.bots.contracts_bot import ContractsBot

    target_path = Path(target_dir).expanduser().resolve() if target_dir else None
    canon_path = Path(canonical_dir).expanduser().resolve() if canonical_dir else None
    bot = ContractsBot(canonical_dir=canon_path)
    res = bot.validate_contracts(target_dir=target_path)

    response = _build_response(
        ctx,
        command="contracts.validate",
        state="ok" if res.get("state") == "ok" else "warning",
        data=res,
    )

    def _text() -> None:
        if not res.get("success"):
            console.print(f"[bold red]✗ Validation failed:[/bold red] {res.get('error')}")
            return

        summary = res.get("summary", {})
        schemas = res.get("schemas", [])

        console.print(f"[bold cyan]Canonical Schemas:[/bold cyan] {res.get('canonical_dir')}")
        console.print(f"[bold cyan]Local Schemas:[/bold cyan] {res.get('local_dir')}")

        table = Table(title="Schema Contracts Parity")
        table.add_column("Schema File", style="bold")
        table.add_column("Status")
        table.add_column("Canonical")
        table.add_column("Local")
        table.add_column("Details")

        status_styles = {
            "in_sync": ("green", "✓ IN_SYNC"),
            "drifted": ("yellow", "⚠ DRIFTED"),
            "missing_local": ("red", "✗ MISSING"),
            "untracked": ("magenta", "? UNTRACKED"),
            "invalid": ("bold red", "✗ INVALID"),
        }

        for item in schemas:
            st = item.get("status", "unknown")
            color, label = status_styles.get(st, ("white", st.upper()))
            diff = item.get("diff") or ""
            table.add_row(
                item.get("schema", ""),
                f"[{color}]{label}[/{color}]",
                "✓" if item.get("in_canonical") else "-",
                "✓" if item.get("in_local") else "-",
                diff,
            )
        console.print(table)

        console.print(
            f"Summary: [bold]{summary.get('in_sync', 0)}[/bold] in sync, "
            f"[bold yellow]{summary.get('drifted', 0)}[/bold yellow] drifted, "
            f"[bold red]{summary.get('missing_local', 0)}[/bold red] missing locally, "
            f"[bold magenta]{summary.get('untracked', 0)}[/bold magenta] untracked."
        )

    _emit_response(ctx, response, text_renderer=_text)


@contracts.command("sync")
@click.option("--target-dir", default=None, help="Target repository directory to synchronize contracts into.")
@click.option("--canonical-dir", default=None, help="Canonical contracts directory to synchronize from.")
@click.option("--dry-run", is_flag=True, help="Simulate synchronization without modifying files.")
@click.pass_context
def contracts_sync(ctx: click.Context, target_dir: str | None, canonical_dir: str | None, dry_run: bool) -> None:
    """Synchronize canonical schemas into target repository contracts directory."""
    from hath0r_cli.bots.contracts_bot import ContractsBot

    target_path = Path(target_dir).expanduser().resolve() if target_dir else None
    canon_path = Path(canonical_dir).expanduser().resolve() if canonical_dir else None
    bot = ContractsBot(canonical_dir=canon_path)
    res = bot.sync_contracts(target_dir=target_path, dry_run=dry_run)

    response = _build_response(
        ctx,
        command="contracts.sync",
        state="ok" if res.get("success") else "error",
        data=res,
        dry_run=dry_run,
    )

    def _text() -> None:
        if not res.get("success"):
            console.print(f"[bold red]✗ Sync failed:[/bold red] {res.get('error')}")
            return

        synced = res.get("synced_schemas", [])
        if synced:
            console.print(f"[bold green]✓ {res.get('message')}[/bold green]")
            for s in synced:
                console.print(f"  • {s}")
        else:
            console.print("[green]✓ All local schema contracts are already up to date with canonical definitions.[/green]")

    _emit_response(ctx, response, text_renderer=_text)
