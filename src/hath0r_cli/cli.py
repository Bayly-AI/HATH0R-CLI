"""HATH0R CLI entrypoint."""

from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from hath0r_cli import __version__
from hath0r_cli.envelope import CliResponse, Diagnostic, ResponseMeta
from hath0r_cli.output import OUTPUT_CHOICES, emit, progress_err, resolve_output_mode

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


def _utc_now() -> str:
    """RFC 3339 UTC timestamp with second precision and Z suffix."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _duration_ms(ctx: click.Context) -> int:
    started = ctx.obj.get("started_at", time.perf_counter())
    return max(0, int((time.perf_counter() - started) * 1000))


def _output_mode(ctx: click.Context) -> str:
    return resolve_output_mode(ctx.obj.get("output", "auto"))


def _quiet(ctx: click.Context) -> bool:
    return bool(ctx.obj.get("quiet", False))


def _build_response(
    ctx: click.Context,
    *,
    command: str,
    state: str = "ok",
    data: dict | None = None,
    diagnostics: list[Diagnostic] | None = None,
) -> CliResponse:
    return CliResponse(
        command=command,
        generated_at=_utc_now(),
        state=state,
        data=data,
        diagnostics=list(diagnostics or []),
        meta=ResponseMeta(cli_version=__version__, duration_ms=_duration_ms(ctx)),
    )


def _emit_response(
    ctx: click.Context,
    response: CliResponse,
    *,
    text_renderer=None,
) -> None:
    mode = ctx.obj.get("output", "auto")
    emit(response, mode, console, text_renderer=text_renderer)


@click.group(invoke_without_command=True)
@click.option(
    "--output",
    "-o",
    type=click.Choice(OUTPUT_CHOICES, case_sensitive=False),
    default="auto",
    show_default=True,
    help="Output format: json, text, or auto (TTY→text, non-TTY→json).",
)
@click.option(
    "--quiet",
    is_flag=True,
    default=False,
    help="Suppress stderr progress/warnings (especially in json mode).",
)
@click.option(
    "--version",
    is_flag=True,
    default=False,
    help="Show the hath0r version and exit.",
)
@click.pass_context
def main(ctx: click.Context, output: str, quiet: bool, version: bool) -> None:
    """HATH0R CLI — control plane for the HATHOR OpenSource group."""
    ctx.ensure_object(dict)
    ctx.obj["output"] = output.lower()
    ctx.obj["quiet"] = quiet
    ctx.obj["started_at"] = time.perf_counter()

    if version:
        _emit_version(ctx)
        ctx.exit(0)

    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


def _emit_version(ctx: click.Context) -> None:
    response = _build_response(
        ctx,
        command="version",
        state="ok",
        data={
            "binary": "hath0r",
            "package": "hath0r-cli",
            "version": __version__,
        },
    )

    def _text() -> None:
        click.echo(f"hath0r, version {__version__}")

    _emit_response(ctx, response, text_renderer=_text)


def _file_contains(path: Path, needle: str) -> bool:
    if not path.is_file():
        return False
    try:
        return needle in path.read_text(encoding="utf-8")
    except OSError:
        return False


@main.command()
@click.pass_context
def doctor(ctx: click.Context) -> None:
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

    state = "ok" if failures == 0 else "degraded"
    response = _build_response(
        ctx,
        command="doctor",
        state=state,
        data=None,  # full payload lands in a follow-up issue
        diagnostics=[],
    )

    def _text() -> None:
        console.print(table)
        console.print(f"hath0r {__version__}")
        if failures:
            console.print(f"[red]doctor failed: {failures} check(s)[/red]")
        else:
            console.print("[green]doctor passed: OpenSource control tower configuration ok[/green]")

    _emit_response(ctx, response, text_renderer=_text)
    if failures:
        raise SystemExit(1)


@main.group()
def kb() -> None:
    """Knowledgebase helpers (group hub)."""


@kb.command("path")
@click.pass_context
def kb_path(ctx: click.Context) -> None:
    """Print the canonical OpenSource group knowledgebase path."""
    path = _kb_path()
    missing = not path.is_dir()
    diagnostics: list[Diagnostic] = []
    state = "ok"
    if missing:
        state = "unavailable"
        diagnostics.append(
            Diagnostic(
                code="KNOWLEDGEBASE_NOT_FOUND",
                message="The canonical OpenSource knowledgebase is unavailable.",
                severity="error",
                remediation="Verify the group root and run hath0r doctor.",
                provenance={"component": "hath0r-cli", "operation": "kb.path"},
            )
        )

    response = _build_response(
        ctx,
        command="kb.path",
        state=state,
        data=None,  # full payload lands in a follow-up issue
        diagnostics=diagnostics,
    )

    def _text() -> None:
        click.echo(str(path))
        if missing:
            raise SystemExit(f"knowledgebase missing: {path}")

    if _output_mode(ctx) == "json":
        # Progress/status belongs on stderr and is suppressed by --quiet.
        progress_err("resolving knowledgebase path", quiet=_quiet(ctx))
        _emit_response(ctx, response)
        if missing:
            raise SystemExit(3)
    else:
        _emit_response(ctx, response, text_renderer=_text)


@kb.command("products")
@click.pass_context
def kb_products(ctx: click.Context) -> None:
    """List canonical suite products from the group catalog."""
    catalog = _kb_path() / "catalogs" / "suite-products.yaml"
    missing = not catalog.is_file()
    diagnostics: list[Diagnostic] = []
    state = "ok"
    catalog_text = ""
    if missing:
        state = "unavailable"
        diagnostics.append(
            Diagnostic(
                code="PRODUCT_CATALOG_NOT_FOUND",
                message="The suite products catalog is unavailable.",
                severity="error",
                remediation="Verify the knowledgebase path and run hath0r doctor.",
                provenance={"component": "hath0r-cli", "operation": "kb.products"},
            )
        )
    else:
        catalog_text = catalog.read_text(encoding="utf-8")

    response = _build_response(
        ctx,
        command="kb.products",
        state=state,
        data=None,  # full payload lands in a follow-up issue
        diagnostics=diagnostics,
    )

    def _text() -> None:
        if missing:
            raise SystemExit(f"catalog missing: {catalog}")
        click.echo(catalog_text)

    if _output_mode(ctx) == "json":
        _emit_response(ctx, response)
        if missing:
            raise SystemExit(3)
    else:
        _emit_response(ctx, response, text_renderer=_text)


if __name__ == "__main__":
    main()
