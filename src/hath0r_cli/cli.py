"""HATH0R CLI entrypoint."""

from __future__ import annotations

import os
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from hath0r_cli import __version__

console = Console()

DEFAULT_GROUP_ROOT = Path("/Users/raybayly/Development/OpenSource")
DEFAULT_KB = DEFAULT_GROUP_ROOT / ".hath0r" / "knowledgebase"


def _group_root() -> Path:
    return Path(os.environ.get("HATH0R_GROUP_ROOT", DEFAULT_GROUP_ROOT)).expanduser()


def _kb_path() -> Path:
    override = os.environ.get("HATH0R_KB_PATH")
    if override:
        return Path(override).expanduser()
    return _group_root() / ".hath0r" / "knowledgebase"


@click.group()
@click.version_option(__version__, prog_name="hath0r")
def main() -> None:
    """HATH0R CLI — control plane for the HATHOR OpenSource group."""


@main.command()
def doctor() -> None:
    """Check group paths, member repos, and KB hub presence."""
    root = _group_root()
    kb = _kb_path()
    members = {
        "framework": root / "hath0r",
        "cli": root / "HATH0R-CLI",
        "poc": root / "hath0r-poc",
    }

    table = Table(title="HATH0R doctor")
    table.add_column("Check")
    table.add_column("Path")
    table.add_column("Status")

    def status(path: Path, want_dir: bool = True) -> str:
        ok = path.is_dir() if want_dir else path.is_file()
        return "[green]ok[/green]" if ok else "[red]missing[/red]"

    table.add_row("group root", str(root), status(root))
    table.add_row("canonical KB", str(kb), status(kb))
    table.add_row("suite catalog", str(kb / "catalogs" / "suite-products.yaml"), status(kb / "catalogs" / "suite-products.yaml", want_dir=False))
    for name, path in members.items():
        table.add_row(f"member:{name}", str(path), status(path))
        table.add_row(f"agents:{name}", str(path / "AGENTS.md"), status(path / "AGENTS.md", want_dir=False))

    console.print(table)
    console.print(f"hath0r {__version__}")


@main.group()
def kb() -> None:
    """Knowledgebase helpers (group hub)."""


@kb.command("path")
def kb_path() -> None:
    """Print the canonical OpenSource group knowledgebase path."""
    path = _kb_path()
    click.echo(str(path))
    if not path.is_dir():
        raise SystemExit(f"knowledgebase missing: {path}")


@kb.command("products")
def kb_products() -> None:
    """List canonical suite products from the group catalog."""
    catalog = _kb_path() / "catalogs" / "suite-products.yaml"
    if not catalog.is_file():
        raise SystemExit(f"catalog missing: {catalog}")
    # Minimal YAML-free display: print file for operators; full parse comes later.
    click.echo(catalog.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
