"""HATH0R CLI entrypoint — modular control plane for the HATHOR OpenSource group."""

from __future__ import annotations

import sys
import time

import click

from hath0r_cli import __version__
from hath0r_cli.commands import register_all_commands
from hath0r_cli.common import (
    _GROUP_MARKER,
    _GROUP_ROOT_ERROR,
    _SOFT_FALLBACK_GROUP_ROOT,
    _build_response,
    _discover_group_root,
    _duration_ms,
    _emit_response,
    _group_root,
    _kb_path,
    _looks_like_group_root,
    _output_mode,
    _quiet,
    _utc_now,
    console,
)
from hath0r_cli.lazy_group import Hath0rLazyGroup
from hath0r_cli.output import OUTPUT_CHOICES


def _resolve_target_repos(*args, **kwargs):
    """Lazy resolution helper for target repositories."""
    from hath0r_cli.commands.repo import _resolve_target_repos as _resolver

    return _resolver(*args, **kwargs)


@click.group(cls=Hath0rLazyGroup, invoke_without_command=True)
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
    "--verbose",
    is_flag=True,
    default=False,
    help="Include absolute local paths in structured doctor diagnostics.",
)
@click.option(
    "--version",
    is_flag=True,
    default=False,
    help="Show the hath0r version and exit.",
)
@click.pass_context
def main(ctx: click.Context, output: str, quiet: bool, verbose: bool, version: bool) -> None:
    """HATH0R CLI — control plane for the HATHOR OpenSource group."""
    ctx.ensure_object(dict)
    ctx.obj["output"] = output.lower()
    ctx.obj["quiet"] = quiet
    ctx.obj["verbose"] = verbose
    ctx.obj["started_at"] = time.perf_counter()

    if version:
        _emit_version(ctx)
        ctx.exit(0)

    if not quiet:
        _check_cccd_freshness_gate(ctx)

    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


def _check_cccd_freshness_gate(ctx: click.Context) -> None:
    """Canonical Entry Gate: Verify CCCD calibration age is <= 24 hours."""
    if (
        ctx.obj.get("quiet")
        or ctx.invoked_subcommand == "cccd"
        or "--json" in sys.argv
        or "-j" in sys.argv
    ):
        return

    try:
        from rich.console import Console
        from rich.panel import Panel

        from hath0r_cli.cccd.calibration_loop import CCCDCalibrationLoop

        freshness = CCCDCalibrationLoop().check_calibration_freshness(max_age_hours=24.0)
        if freshness.get("stale"):
            age_msg = f"{freshness['age_hours']:.1f} hours ago" if freshness.get("age_hours") is not None else "Never"
            msg = (
                f"[bold yellow]⚠️ [CRITICAL ENTRY GATE] CCCD Calibration is Stale (>24h Limit)[/bold yellow]\n\n"
                f"Last Calibration Run: [bold white]{age_msg}[/bold white]\n"
                f"Status: Prompt signatures and runtime parameters require re-calibration.\n\n"
                f"[bold cyan]Offer:[/bold cyan] Run [bold green]hath0r cccd calibrate[/bold green] to re-calibrate parameters."
            )
            err_console = Console(stderr=True)
            err_console.print(Panel(msg, title="CCCD Calibration Entry Gate", border_style="bold yellow"))
    except Exception:
        pass


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


# Register all modular command groups on lazy group
register_all_commands(main)


__all__ = [
    "main",
    "_group_root",
    "_looks_like_group_root",
    "_discover_group_root",
    "_kb_path",
    "_utc_now",
    "_duration_ms",
    "_output_mode",
    "_quiet",
    "_build_response",
    "_emit_response",
    "_resolve_target_repos",
    "_SOFT_FALLBACK_GROUP_ROOT",
    "_GROUP_MARKER",
    "_GROUP_ROOT_ERROR",
    "console",
]
