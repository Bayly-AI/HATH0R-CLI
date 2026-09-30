"""HATH0R CLI entrypoint — modular control plane for the HATHOR OpenSource group."""

from __future__ import annotations

import time

import click

from hath0r_cli import __version__
from hath0r_cli.commands import register_all_commands
from hath0r_cli.commands.repo import _resolve_target_repos
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
from hath0r_cli.output import OUTPUT_CHOICES
from hath0r_cli.telemetry import init_tracer


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

    init_tracer()

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


# Register all modular command groups
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
