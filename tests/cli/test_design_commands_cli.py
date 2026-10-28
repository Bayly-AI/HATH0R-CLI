"""CLI tests for `hath0r design`, exercising the offline Paper.design paths."""

from __future__ import annotations

import json

import pytest
from click.testing import CliRunner

from hath0r_cli.bots.paper_design_bot import PaperConnectionReport, PaperDesignBot
from hath0r_cli.cli import main

HTML = '<div class="hero" style="color:#ff0000;padding:16px;font-family:Inter"><h1>Hi</h1><img src="a.png"></div>'


def _run(fmt: str, *args: str):
    return CliRunner().invoke(main, ["-o", fmt, "design", *args])


@pytest.fixture
def files(tmp_path):
    html = tmp_path / "hero.html"
    html.write_text(HTML, encoding="utf-8")
    mock = tmp_path / "sel.json"
    mock.write_text(json.dumps({"selection": [{"id": "1", "name": "Hero", "type": "frame"}]}), encoding="utf-8")
    return tmp_path, html, mock


@pytest.mark.parametrize("fmt", ["text", "json"], ids=["text", "json"])
@pytest.mark.parametrize("online", [True, False], ids=["online", "offline"])
def test_design_status(monkeypatch, fmt, online):
    report = PaperConnectionReport(
        status="online" if online else "offline",
        connected=online,
        transport="streamable-http" if online else "none",
        url="http://127.0.0.1:1",
        cli_path="/usr/bin/paper" if online else None,
        tools_available=["get_selection"] if online else [],
        message="ok" if online else "down",
        remediation=None if online else "start Paper",
    )
    monkeypatch.setattr(PaperDesignBot, "check_connection", lambda self, timeout=1.5: report)
    res = _run(fmt, "status", "--url", "http://127.0.0.1:1")
    assert res.exception is None or isinstance(res.exception, SystemExit), res.output
    assert res.output.strip()


@pytest.mark.parametrize("fmt", ["text", "json"], ids=["text", "json"])
def test_design_offline_commands(files, fmt):
    tmp_path, html, mock = files
    out = tmp_path / "Hero.tsx"
    cases = [
        ("inspect",),
        ("inspect", "--mock", str(mock)),
        ("to-code", "-i", str(html), "-n", "Hero", "-f", "react_tailwind", "-o", str(out)),
        ("to-code", "-i", str(html), "-f", "html_css"),
        ("to-code",),
        ("to-canvas", "-i", str(html), "--name", "Board", "-w", "800", "-h", "600"),
        ("tokens", str(html)),
        ("audit", str(html)),
    ]
    for args in cases:
        res = _run(fmt, *args)
        assert res.exception is None or isinstance(res.exception, SystemExit), (args, res.output)
        assert res.output.strip(), args


def test_design_group_help():
    assert "design" in CliRunner().invoke(main, ["design", "--help"]).output.lower()
