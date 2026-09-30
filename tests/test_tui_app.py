"""Unit tests for HathorTUIApp and tui CLI command."""

from click.testing import CliRunner
from rich.layout import Layout
from rich.panel import Panel

from hath0r_cli.cli import main
from hath0r_cli.ui.tui_app import HathorTUIApp


def test_tui_panels_generation():
    app = HathorTUIApp()

    p_overview = app.build_system_overview_panel()
    assert isinstance(p_overview, Panel)

    p_graphs = app.build_cognitive_graphs_panel()
    assert isinstance(p_graphs, Panel)

    p_safety = app.build_mcp_and_safety_panel()
    assert isinstance(p_safety, Panel)


def test_tui_render_snapshot():
    app = HathorTUIApp()
    layout = app.render_snapshot()
    assert isinstance(layout, Layout)
    assert "header" in [c.name for c in layout.children]
    assert "body" in [c.name for c in layout.children]
    assert "footer" in [c.name for c in layout.children]


def test_cli_tui_command():
    runner = CliRunner()
    result = runner.invoke(main, ["tui", "--mode", "snapshot"])
    assert result.exit_code == 0
    assert "HATH0R Control Plane" in result.output
    assert "Cognitive Substrate" in result.output
    assert "Security & Capabilities" in result.output
