"""Unit tests for Hath0r FastMCP server and Claude Desktop connector."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from hath0r_cli.cli import main as cli
from hath0r_cli.server.mcp_server import (
    create_mcp_server,
    install_claude_desktop_connector,
)


def test_create_mcp_server():
    """Verify FastMCP server instance creation and registered tools."""
    server = create_mcp_server()
    assert server is not None
    assert server.name == "hath0r-cli"


def test_install_claude_desktop_connector():
    """Verify writing connector entry into temporary Claude config file."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        config_path = Path(tmp_dir) / "claude_desktop_config.json"
        with patch("hath0r_cli.server.mcp_server.get_claude_desktop_config_path", return_value=config_path):
            res = install_claude_desktop_connector(server_name="hath0r-test", hath0r_binary="/usr/local/bin/hath0r")
            assert res["success"] is True
            assert config_path.exists()

            payload = json.loads(config_path.read_text(encoding="utf-8"))
            assert "mcpServers" in payload
            assert "hath0r-test" in payload["mcpServers"]
            assert payload["mcpServers"]["hath0r-test"]["command"] == "/usr/local/bin/hath0r"
            assert payload["mcpServers"]["hath0r-test"]["args"] == ["mcp", "serve"]


def test_mcp_serve_install_claude_only_cli():
    """Verify hath0r mcp serve --install-claude-only flag."""
    runner = CliRunner()
    with tempfile.TemporaryDirectory() as tmp_dir:
        config_path = Path(tmp_dir) / "claude_desktop_config.json"
        with patch("hath0r_cli.server.mcp_server.get_claude_desktop_config_path", return_value=config_path):
            res = runner.invoke(
                cli,
                [
                    "-o",
                    "text",
                    "mcp",
                    "serve",
                    "--install-claude-only",
                    "--binary",
                    "/usr/local/bin/hath0r",
                ],
            )
            assert res.exit_code == 0
            assert "HATH0R CLI Connector Registered" in res.output

            payload = json.loads(config_path.read_text(encoding="utf-8"))
            assert "hath0r-cli" in payload["mcpServers"]
