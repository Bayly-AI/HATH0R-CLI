"""Output mode resolution and response emission."""

from __future__ import annotations

import json
import sys
from collections.abc import Callable
from typing import TextIO

from rich.console import Console

from hath0r_cli.envelope import CliResponse

OUTPUT_CHOICES = ("json", "text", "auto")


def resolve_output_mode(mode: str, *, stdout: TextIO | None = None) -> str:
    """Resolve ``auto`` to ``json`` (non-TTY) or ``text`` (TTY); pass through otherwise."""
    if mode != "auto":
        return mode
    stream = stdout if stdout is not None else sys.stdout
    isatty = getattr(stream, "isatty", lambda: False)
    return "text" if isatty() else "json"


def emit_json(response: CliResponse, *, stream: TextIO | None = None) -> None:
    """Write one UTF-8 JSON document plus final newline to stdout (no ANSI)."""
    out = stream if stream is not None else sys.stdout
    payload = response.to_dict()
    # ensure_ascii keeps output plain; no Rich/ANSI on this path.
    out.write(json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=False))
    out.write("\n")
    out.flush()


def emit(
    response: CliResponse,
    output_mode: str,
    console: Console | None = None,
    *,
    text_renderer: Callable[[], None] | None = None,
    stdout: TextIO | None = None,
) -> str:
    """Emit a response in the resolved mode.

    Returns the resolved mode (``json`` or ``text``).

    - ``json``: serialize envelope to stdout with no ANSI.
    - ``text``: call ``text_renderer`` if provided; otherwise no-op (caller already rendered).
    - ``auto``: resolve via TTY detection first.
    """
    resolved = resolve_output_mode(output_mode, stdout=stdout)
    if resolved == "json":
        emit_json(response, stream=stdout)
    elif text_renderer is not None:
        text_renderer()
    return resolved


def progress_err(message: str, *, quiet: bool, stream: TextIO | None = None) -> None:
    """Write a progress/warning line to stderr unless ``quiet`` is set."""
    if quiet:
        return
    err = stream if stream is not None else sys.stderr
    err.write(message)
    if not message.endswith("\n"):
        err.write("\n")
    err.flush()
