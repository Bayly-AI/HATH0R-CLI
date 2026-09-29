"""Playbook command for HATH0R CLI."""

from __future__ import annotations

from pathlib import Path

import click

from hath0r_cli.common import (
    _build_response,
    _emit_response,
    console,
)


@click.group()
def playbook() -> None:
    """Read and list Hath0r diagnostic and operational playbooks."""
    pass


@playbook.command("list")
@click.pass_context
def playbook_list(ctx: click.Context) -> None:
    """List available playbooks."""

    playbooks_dir = Path("docs/governance/playbooks")
    playbooks = []
    if playbooks_dir.exists():
        for p in playbooks_dir.glob("*.md"):
            playbooks.append(p.stem)

    response = _build_response(ctx, command="playbook.list", state="ok", data={"playbooks": playbooks})

    def _text() -> None:
        console.print("[bold cyan]Available Playbooks:[/bold cyan]")
        for pb in playbooks:
            console.print(f"  • {pb}")

    _emit_response(ctx, response, text_renderer=_text)


@playbook.command("read")
@click.argument("name")
@click.pass_context
def playbook_read(ctx: click.Context, name: str) -> None:
    """Read a specific playbook by name (e.g. playbook-troubleshooting)."""

    target = Path(f"docs/governance/playbooks/{name}.md")
    content = ""
    success = False

    if target.exists():
        content = target.read_text(encoding="utf-8")
        success = True

    response = _build_response(
        ctx,
        command="playbook.read",
        state="ok" if success else "error",
        data={"name": name, "content": content, "success": success},
    )

    def _text() -> None:
        if success:
            from rich.markdown import Markdown

            console.print(Markdown(content))
        else:
            console.print(f"[bold red]✗ Playbook not found:[/bold red] {name}")

    _emit_response(ctx, response, text_renderer=_text)



