"""HATH0R CLI entrypoint."""

from __future__ import annotations

import os
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from hath0r_cli import __version__

console = Console()

# Soft fallback only — used when it looks like a real group root.
_SOFT_FALLBACK_GROUP_ROOT = Path.home() / "Development" / "OpenSource"

_GROUP_MARKER = "hath0r-opensource"
_GROUP_ROOT_ERROR = (
    "Could not determine HATHOR OpenSource group root.\n"
    "Remediation:\n"
    "  1. Set HATH0R_GROUP_ROOT to the directory that contains AGENTS.md "
    f"(with '{_GROUP_MARKER}') and a .hath0r/ directory, or\n"
    "  2. Run the CLI from inside that group tree so walk-up discovery can find it, or\n"
    "  3. Place the group at ~/Development/OpenSource with the same markers."
)


def _looks_like_group_root(path: Path) -> bool:
    """Return True if path has AGENTS.md containing the group marker and a .hath0r/ dir."""
    agents = path / "AGENTS.md"
    hath0r_dir = path / ".hath0r"
    if not agents.is_file() or not hath0r_dir.is_dir():
        return False
    try:
        return _GROUP_MARKER in agents.read_text(encoding="utf-8")
    except OSError:
        return False


def _discover_group_root(start: Path | None = None) -> Path | None:
    """Walk up from start (default: cwd) looking for a group root.

    When multiple ancestors match (member checkout nested under the group),
    prefer the outermost match so the true group root wins.
    """
    current = (start or Path.cwd()).resolve()
    found: Path | None = None
    for candidate in (current, *current.parents):
        if _looks_like_group_root(candidate):
            found = candidate
    return found


def _group_root() -> Path:
    """Resolve the OpenSource group root.

    Discovery order:
    1. HATH0R_GROUP_ROOT environment variable (if set)
    2. Walk up from cwd for AGENTS.md containing 'hath0r-opensource' plus .hath0r/
    3. Soft fallback ~/Development/OpenSource if it looks like the group root
    4. Clear error with remediation
    """
    env = os.environ.get("HATH0R_GROUP_ROOT")
    if env:
        return Path(env).expanduser().resolve()

    found = _discover_group_root()
    if found is not None:
        return found

    soft = _SOFT_FALLBACK_GROUP_ROOT.expanduser()
    if _looks_like_group_root(soft):
        return soft.resolve()

    raise click.ClickException(_GROUP_ROOT_ERROR)


def _kb_path() -> Path:
    override = os.environ.get("HATH0R_KB_PATH")
    if override:
        return Path(override).expanduser()
    return _group_root() / ".hath0r" / "knowledgebase"


@click.group()
@click.version_option(__version__, prog_name="hath0r")
def main() -> None:
    """HATH0R CLI — control plane for the HATHOR OpenSource group."""


def _file_contains(path: Path, needle: str) -> bool:
    if not path.is_file():
        return False
    try:
        return needle in path.read_text(encoding="utf-8")
    except OSError:
        return False


@main.command()
def doctor() -> None:
    """Check group paths, control tower, member repos, and KB hub presence."""
    root = _group_root()
    kb = _kb_path()
    tower = root / "HATH0R-CLI"
    tower_cfg = tower / "cfg"
    members = {
        "framework": root / "hath0r",
        "cli": tower,
        "poc": root / "hath0r-poc",
    }
    expected_tower = str(tower)

    table = Table(title="HATH0R doctor — OpenSource control tower")
    table.add_column("Check")
    table.add_column("Path / detail")
    table.add_column("Status")

    failures = 0

    def row(check: str, detail: str, ok: bool, bad: str = "missing") -> None:
        nonlocal failures
        if not ok:
            failures += 1
        table.add_row(
            check,
            detail,
            "[green]ok[/green]" if ok else f"[red]{bad}[/red]",
        )

    def status_path(path: Path, want_dir: bool = True) -> bool:
        return path.is_dir() if want_dir else path.is_file()

    row("group root", str(root), status_path(root))
    row("group AGENTS.md", str(root / "AGENTS.md"), status_path(root / "AGENTS.md", want_dir=False))
    row("group WARP.md", str(root / "WARP.md"), status_path(root / "WARP.md", want_dir=False))
    row("canonical KB", str(kb), status_path(kb))
    catalog = kb / "catalogs" / "suite-products.yaml"
    row("suite catalog", str(catalog), status_path(catalog, want_dir=False))
    row(
        "catalog tower path",
        expected_tower,
        _file_contains(catalog, expected_tower),
        bad="mismatch",
    )

    # Control tower identity (this CLI repo)
    row("control tower root", str(tower), status_path(tower))
    for name in ("control-tower.yaml", "suite.yaml", "knowledge-tower.yaml", "products.yaml"):
        path = tower_cfg / name
        row(f"tower cfg:{name}", str(path), status_path(path, want_dir=False))

    kt = tower_cfg / "knowledge-tower.yaml"
    row(
        "tower is_control_tower",
        "is_control_tower: true",
        _file_contains(kt, "is_control_tower: true"),
        bad="false/missing",
    )
    row(
        "tower control_tower_path",
        expected_tower,
        _file_contains(kt, expected_tower) and _file_contains(tower_cfg / "suite.yaml", expected_tower),
        bad="mismatch",
    )
    row(
        "tower remote",
        "Bayly-AI/HATH0R-CLI",
        _file_contains(tower_cfg / "control-tower.yaml", "Bayly-AI/HATH0R-CLI"),
        bad="mismatch",
    )

    for name, path in members.items():
        row(f"member:{name}", str(path), status_path(path))
        row(f"agents:{name}", str(path / "AGENTS.md"), status_path(path / "AGENTS.md", want_dir=False))
        member_kt = path / "cfg" / "knowledge-tower.yaml"
        member_suite = path / "cfg" / "suite.yaml"
        if name == "cli":
            continue
        if member_kt.is_file() or member_suite.is_file():
            ok_pointer = True
            if member_kt.is_file():
                ok_pointer = ok_pointer and _file_contains(member_kt, expected_tower)
                ok_pointer = ok_pointer and _file_contains(member_kt, "is_control_tower: false")
            if member_suite.is_file():
                ok_pointer = ok_pointer and _file_contains(member_suite, expected_tower)
            row(
                f"member tower pointer:{name}",
                expected_tower,
                ok_pointer,
                bad="mismatch",
            )
        else:
            # Framework may only document tower in AGENTS.md
            row(
                f"member tower pointer:{name}",
                str(path / "AGENTS.md"),
                _file_contains(path / "AGENTS.md", "HATH0R-CLI"),
                bad="mismatch",
            )

    console.print(table)
    console.print(f"hath0r {__version__}")
    if failures:
        console.print(f"[red]doctor failed: {failures} check(s)[/red]")
        raise SystemExit(1)
    console.print("[green]doctor passed: OpenSource control tower configuration ok[/green]")


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
