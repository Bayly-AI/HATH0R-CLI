"""Code intelligence and AST structural inspection commands for Hath0r CLI."""

from __future__ import annotations

import json
from pathlib import Path

import click

from hath0r_cli.code_parser import CodeParser
from hath0r_cli.common import (
    _build_response,
    _emit_response,
)


@click.group("code")
def code() -> None:
    """Code intelligence — AST outlining, symbol indexing, and syntax validation."""


@code.command("outline")
@click.argument("file_path", type=click.Path(exists=True, path_type=Path))
@click.option("--language", "-l", default=None, help="Explicit programming language override.")
@click.pass_context
def code_outline(ctx: click.Context, file_path: Path, language: str | None) -> None:
    """Generate a compact structural outline for LLM context injection."""
    parser = CodeParser()
    lang = language or parser.detect_language(file_path)
    code_text = file_path.read_text(encoding="utf-8")

    symbols = parser.extract_symbols(code_text, language=lang)
    outline = parser.generate_outline(code_text, language=lang)

    response = _build_response(
        ctx,
        command="code.outline",
        state="ok",
        data={
            "file": str(file_path),
            "language": lang,
            "symbol_count": len(symbols),
            "outline": outline,
            "symbols": [s.to_dict() for s in symbols],
        },
    )

    def _text() -> None:
        click.echo(f"=== Structural Outline: {file_path.name} ({lang}) ===")
        click.echo(outline)

    _emit_response(ctx, response, text_renderer=_text)


@code.command("symbols")
@click.argument("file_path", type=click.Path(exists=True, path_type=Path))
@click.option("--language", "-l", default=None, help="Explicit programming language override.")
@click.pass_context
def code_symbols(ctx: click.Context, file_path: Path, language: str | None) -> None:
    """Extract and list indexed symbols with line numbers."""
    parser = CodeParser()
    lang = language or parser.detect_language(file_path)
    code_text = file_path.read_text(encoding="utf-8")

    symbols = parser.extract_symbols(code_text, language=lang)

    response = _build_response(
        ctx,
        command="code.symbols",
        state="ok",
        data={
            "file": str(file_path),
            "language": lang,
            "symbols": [s.to_dict() for s in symbols],
        },
    )

    def _text() -> None:
        click.echo(f"Found {len(symbols)} symbols in {file_path.name}:")
        for sym in symbols:
            click.echo(f"  [{sym.symbol_type}] {sym.name} (lines {sym.line_start}-{sym.line_end})")
            for ch in sym.children:
                click.echo(f"    └─ [{ch.symbol_type}] {ch.name} (lines {ch.line_start}-{ch.line_end})")

    _emit_response(ctx, response, text_renderer=_text)


@code.command("validate")
@click.argument("file_path", type=click.Path(exists=True, path_type=Path))
@click.option("--language", "-l", default=None, help="Explicit programming language override.")
@click.pass_context
def code_validate(ctx: click.Context, file_path: Path, language: str | None) -> None:
    """Validate syntax structure and bracket integrity before saving."""
    parser = CodeParser()
    lang = language or parser.detect_language(file_path)
    code_text = file_path.read_text(encoding="utf-8")

    is_valid, error_msg = parser.validate_syntax(code_text, language=lang)

    state = "ok" if is_valid else "error"
    response = _build_response(
        ctx,
        command="code.validate",
        state=state,
        data={
            "file": str(file_path),
            "language": lang,
            "valid": is_valid,
            "error": error_msg,
        },
    )

    def _text() -> None:
        if is_valid:
            click.echo(f"✓ Syntax valid for {file_path.name} ({lang}).")
        else:
            click.echo(f"✗ Syntax error in {file_path.name}: {error_msg}")

    _emit_response(ctx, response, text_renderer=_text)
    if not is_valid:
        ctx.exit(1)
