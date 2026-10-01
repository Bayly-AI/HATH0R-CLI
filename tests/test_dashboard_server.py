"""Unit tests for HathorDashboardServer and serve CLI command."""

import json
import urllib.request

from click.testing import CliRunner

from hath0r_cli.cli import main
from hath0r_cli.server.dashboard_server import HathorDashboardServer


def test_dashboard_server_status_payload():
    server = HathorDashboardServer(host="127.0.0.1", port=9090)
    payload = server.get_status_payload()
    assert "doctor" in payload
    assert "graphs" in payload
    assert "security" in payload
    assert payload["security"]["jev_guard"] == "enforced"


def test_dashboard_http_server_endpoints():
    server = HathorDashboardServer(host="127.0.0.1", port=8989)
    server.start(daemon=True)
    try:
        # Test HTML Dashboard
        req = urllib.request.urlopen("http://127.0.0.1:8989/")
        assert req.status == 200
        content = req.read().decode("utf-8")
        assert "HATH0R Agentic Dashboard" in content

        # Test Status API
        req_api = urllib.request.urlopen("http://127.0.0.1:8989/api/status")
        assert req_api.status == 200
        data = json.loads(req_api.read().decode("utf-8"))
        assert "doctor" in data
        assert "graphs" in data
    finally:
        server.stop()


def test_cli_serve_daemon_command():
    runner = CliRunner()
    result = runner.invoke(main, ["serve", "--port", "8990", "--daemon"])
    assert result.exit_code == 0
    assert "Starting HATH0R Web Dashboard" in result.output
    assert "Server running in background daemon thread" in result.output
