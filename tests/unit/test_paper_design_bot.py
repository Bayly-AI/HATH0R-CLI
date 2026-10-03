"""Unit tests for PaperDesignBot and hath0r design CLI commands."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from hath0r_cli import cli
from hath0r_cli.bots.paper_design_bot import PaperConnectionReport, PaperDesignBot


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def test_check_connection_offline() -> None:
    bot = PaperDesignBot(base_url="http://127.0.0.1:29979", cli_path="/nonexistent/paper")
    with patch("urllib.request.urlopen", side_effect=OSError("Connection refused")):
        report = bot.check_connection()
        assert report.status == "offline"
        assert not report.connected
        assert "not running" in report.message
        assert report.remediation is not None


def test_check_connection_online() -> None:
    bot = PaperDesignBot(base_url="http://127.0.0.1:29979")
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        report = bot.check_connection()
        assert report.status == "online"
        assert report.connected
        assert report.transport == "streamable-http"
        assert "paper:get_selection" in report.tools_available


def test_check_connection_cli_fallback(tmp_path: Path) -> None:
    fake_cli = tmp_path / "paper"
    fake_cli.write_text("#!/bin/sh\necho mcp")
    fake_cli.chmod(0o755)

    bot = PaperDesignBot(base_url="http://127.0.0.1:29979", cli_path=str(fake_cli))
    with patch("urllib.request.urlopen", side_effect=OSError("Connection refused")):
        report = bot.check_connection()
        assert report.status == "cli_available"
        assert report.connected
        assert report.transport == "stdio"
        assert report.cli_path == str(fake_cli)


def test_design_to_code_react_tailwind() -> None:
    bot = PaperDesignBot()
    res = bot.design_to_code(
        raw_design="<h1>Modern Cloud Solutions</h1><p>Scalable infrastructure</p>",
        component_name="hero-section",
        framework="react_tailwind",
    )
    assert res["success"]
    assert res["component_name"] == "HeroSection"
    assert res["framework"] == "react_tailwind"
    assert "import React from 'react';" in res["code"]
    assert "export const HeroSection" in res["code"]
    assert "Modern Cloud Solutions" in res["code"]
    assert "className=" in res["code"]


def test_code_to_design_staging() -> None:
    bot = PaperDesignBot()
    res = bot.code_to_design(
        html_or_jsx="<div><h2>Feature List</h2></div>",
        artboard_name="Features Artboard",
        width=1200,
        height=800,
    )
    assert res["success"]
    assert res["payload"]["tool"] == "paper:write_html"
    assert res["payload"]["artboard"]["name"] == "Features Artboard"
    assert res["payload"]["artboard"]["width"] == 1200
    assert "Feature List" in res["payload"]["html"]


def test_extract_tokens() -> None:
    bot = PaperDesignBot()
    sample_css = """
    .card { background-color: #0f172a; border-color: #38bdf8; }
    .btn { background-color: #6366f1; }
    """
    res = bot.extract_tokens(sample_css)
    assert res["success"]
    assert res["count"] >= 3
    assert ":root" in res["css_variables"]
    assert "colors" in res["tokens"]


def test_audit_layout() -> None:
    bot = PaperDesignBot()
    good_html = """
    <header><nav><a href="#">Home</a></nav></header>
    <main>
      <section>
        <h1>Welcome</h1>
        <img src="/logo.png" alt="Company Logo" />
        <button aria-label="Explore features">Explore</button>
      </section>
    </main>
    <footer><p>Copyright 2026</p></footer>
    """
    res = bot.audit_layout(good_html)
    assert res["success"]
    assert res["status"] == "pass"
    assert res["accessibility_score"] >= 80
    assert "nav" in res["landmarks_detected"]

    bad_html = "<div><img src='test.png'><button></button></div>"
    bad_res = bot.audit_layout(bad_html)
    assert bad_res["success"]
    assert bad_res["accessibility_score"] < 80
    assert len(bad_res["findings"]) >= 2


def test_cli_design_status(runner: CliRunner) -> None:
    mock_report = PaperConnectionReport(
        status="online",
        connected=True,
        transport="streamable-http",
        url="http://127.0.0.1:29979",
        tools_available=["paper:get_selection", "paper:write_html"],
        message="Connected to active Paper Desktop background MCP server.",
    )
    with patch.object(PaperDesignBot, "check_connection", return_value=mock_report):
        res = runner.invoke(cli.main, ["--output", "text", "design", "status"])
        assert res.exit_code == 0
        assert "ONLINE" in res.stdout
        assert "paper:get_selection" in res.stdout

        res_json = runner.invoke(cli.main, ["--output", "json", "design", "status"])
        assert res_json.exit_code == 0
        data = json.loads(res_json.stdout)
        assert data["command"] == "design.status"
        assert data["data"]["connected"] is True


def test_cli_design_to_code(runner: CliRunner, tmp_path: Path) -> None:
    out_file = tmp_path / "Hero.tsx"
    res = runner.invoke(
        cli.main,
        ["design", "to-code", "--name", "LandingHero", "--output", str(out_file)],
    )
    assert res.exit_code == 0
    assert out_file.exists()
    assert "LandingHero" in out_file.read_text()


def test_cli_design_audit(runner: CliRunner, tmp_path: Path) -> None:
    html_file = tmp_path / "page.html"
    html_file.write_text("<main><section><h1>Title</h1></section></main>")
    res = runner.invoke(cli.main, ["--output", "text", "design", "audit", str(html_file)])
    assert res.exit_code == 0
    assert "Web Layout Audit Score" in res.stdout
