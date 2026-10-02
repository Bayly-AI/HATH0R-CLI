"""Unit tests for Hath0r FastMCP server and Claude Desktop connector."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from hath0r_cli.cli import main as cli
from hath0r_cli.server.mcp_server import (
    create_mcp_server,
    install_claude_desktop_connector,
)

pytest.importorskip("mcp")


def test_create_mcp_server():
    """Verify FastMCP server instance creation and registered tools."""
    server = create_mcp_server()
    assert server is not None
    assert server.name == "hath0r-cli"


def test_install_claude_desktop_connector():
    """Verify writing connector entry into temporary Claude config file."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        config_path = Path(tmp_dir) / "claude_desktop_config.json"
        # Use a path that does not need to exist; explicit binary must be preserved.
        binary = str(Path(tmp_dir) / "bin" / "hath0r")
        with patch("hath0r_cli.server.mcp_server.get_claude_desktop_config_path", return_value=config_path):
            res = install_claude_desktop_connector(server_name="hath0r-test", hath0r_binary=binary)
            assert res["success"] is True
            assert config_path.exists()

            payload = json.loads(config_path.read_text(encoding="utf-8"))
            assert "mcpServers" in payload
            assert "hath0r-test" in payload["mcpServers"]
            assert payload["mcpServers"]["hath0r-test"]["command"] == binary
            assert payload["mcpServers"]["hath0r-test"]["args"] == ["mcp", "serve"]


def test_install_claude_desktop_connector_default_resolves_which(tmp_path, monkeypatch):
    """Default binary falls back to PATH when /usr/local/bin/hath0r is missing."""
    config_path = tmp_path / "claude_desktop_config.json"
    fake_bin = tmp_path / "fake-hath0r"
    fake_bin.write_text("#!/bin/sh\n", encoding="utf-8")

    real_exists = Path.exists

    def exists_side_effect(self: Path) -> bool:
        if str(self) == "/usr/local/bin/hath0r":
            return False
        return real_exists(self)

    monkeypatch.setattr(Path, "exists", exists_side_effect)
    monkeypatch.setattr("shutil.which", lambda name: str(fake_bin) if name == "hath0r" else None)
    monkeypatch.setattr(
        "hath0r_cli.server.mcp_server.get_claude_desktop_config_path",
        lambda: config_path,
    )

    res = install_claude_desktop_connector(server_name="hath0r-default")
    assert res["success"] is True
    payload = json.loads(config_path.read_text(encoding="utf-8"))
    assert payload["mcpServers"]["hath0r-default"]["command"] == str(fake_bin)


def test_mcp_serve_install_claude_only_cli():
    """Verify hath0r mcp serve --install-claude-only flag."""
    runner = CliRunner()
    with tempfile.TemporaryDirectory() as tmp_dir:
        config_path = Path(tmp_dir) / "claude_desktop_config.json"
        binary = str(Path(tmp_dir) / "bin" / "hath0r")
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
                    binary,
                ],
            )
            assert res.exit_code == 0, res.output
            assert "HATH0R CLI Connector Registered" in res.output

            payload = json.loads(config_path.read_text(encoding="utf-8"))
            assert "hath0r-cli" in payload["mcpServers"]
            assert payload["mcpServers"]["hath0r-cli"]["command"] == binary
