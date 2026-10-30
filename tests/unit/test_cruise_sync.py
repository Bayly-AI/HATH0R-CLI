"""Cruise Control CLI→server sync, stale-server detection, and detached spawn (#532)."""

from __future__ import annotations

import importlib.util
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest
from click.testing import CliRunner

from hath0r_cli.bots.decision_radar_bot import DecisionRadarBot
from hath0r_cli.commands.decision import decision_cmd
from hath0r_cli.server.decision_radar_server import (
    CRUISE_API_VERSION,
    HathorCruiseControlServer,
    _spawn_detached_daemon_process,
    get_cruise_server_status,
    resolve_cruise_port,
)


class _StaleHandler(BaseHTTPRequestHandler):
    """Mimics a pre-#520 server: status without api_version, 404 on every POST."""

    def do_GET(self) -> None:  # noqa: N802
        body = json.dumps({"success": True, "running": True, "cwd": "/app"}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:  # noqa: N802
        self.send_response(404)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"error": "Endpoint not found"}')

    def log_message(self, *_args: object) -> None:
        pass


@pytest.fixture
def stale_server(monkeypatch: pytest.MonkeyPatch):
    httpd = HTTPServer(("127.0.0.1", 0), _StaleHandler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    port = httpd.server_address[1]
    monkeypatch.setenv("HATH0R_CRUISE_PORT", str(port))
    monkeypatch.setenv("HATH0R_CRUISE_REMOTE_SYNC", "1")
    yield port
    httpd.shutdown()


@pytest.fixture
def live_server(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    server_dir = tmp_path / "server"
    server_dir.mkdir()
    server = HathorCruiseControlServer(host="127.0.0.1", port=0, cwd=server_dir, operator_name="Ray")
    port = server.start(daemon=True)
    monkeypatch.setenv("HATH0R_CRUISE_PORT", str(port))
    monkeypatch.setenv("HATH0R_CRUISE_REMOTE_SYNC", "1")
    yield server, port, server_dir
    server.stop()


def _agent_dir(tmp_path: Path) -> Path:
    d = tmp_path / "agent"
    d.mkdir()
    return d


def test_resolve_cruise_port(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("HATH0R_CRUISE_PORT", raising=False)
    assert resolve_cruise_port() == 38090
    assert resolve_cruise_port(38091) == 38091
    assert resolve_cruise_port(70000) is None
    monkeypatch.setenv("HATH0R_CRUISE_PORT", "not-a-port")
    assert resolve_cruise_port() == 38090


def test_stale_server_failure_is_reported(stale_server: int, tmp_path: Path):
    bot = DecisionRadarBot(cwd=_agent_dir(tmp_path))
    res = bot.update_decision("dec-x", question="q", category="needs_card", upsert=True)
    assert res["success"]  # saved locally
    remote = res["remote_sync"]
    assert remote["synced"] is False
    assert remote["status"] == 404
    assert "stale" in remote["error"]

    status = get_cruise_server_status(cwd=tmp_path / "agent")
    assert status["running"] is True
    assert status["stale"] is True
    assert status["api_version"] is None
    assert status["store_match"] is False


def test_cli_warns_on_stale_server(stale_server: int, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(_agent_dir(tmp_path))
    runner = CliRunner()
    upd = runner.invoke(decision_cmd, ["update", "dec-y", "-q", "q", "--no-split-window"])
    assert upd.exit_code == 0, upd.output
    assert "did not take the update" in upd.output
    dep = runner.invoke(decision_cmd, ["dep", "--from", "a", "--to", "b"])
    assert "did not take the update" in dep.output
    st = runner.invoke(decision_cmd, ["status"])
    assert f"needs v{CRUISE_API_VERSION}" in st.output
    sync = runner.invoke(decision_cmd, ["sync"])
    assert sync.exit_code == 1
    assert "dec-y" in sync.output


def test_sync_store_pushes_open_decisions_and_edges_idempotently(live_server, tmp_path: Path):
    server, port, server_dir = live_server
    agent = DecisionRadarBot(cwd=_agent_dir(tmp_path))
    # Write locally without forwarding, as when the server was down or stale.
    agent.request_decision(decision_id="open-1", question="Open one", note="first note", sync_remote=False)
    agent.request_decision(decision_id="open-2", question="Open two", wait_for_fact="file.exists:x", sync_remote=False)
    agent.request_decision(decision_id="done-1", question="Done", sync_remote=False)
    agent.answer_decision("done-1", answer="ok", sync_remote=False)
    agent.add_task_dependency("open-1", "open-2", sync_remote=False)

    for _ in range(2):
        res = agent.sync_store_to_server()
        assert res["success"], res
        assert sorted(res["pushed"]) == ["open-1", "open-2"]
        assert res["edges_pushed"] == 1

    snap = server.bot.get_radar_snapshot()
    ids = {d["decision_id"]: d for d in snap["decisions"]}
    assert set(ids) >= {"open-1", "open-2"}
    assert "done-1" not in ids
    assert len(ids["open-1"]["notes"]) == 1  # re-sync replaces, it does not append
    store = json.loads((server_dir / ".hath0r" / "decisions" / "active.json").read_text())
    assert store["task_edges"] == [{"from": "open-1", "to": "open-2", "weight": 1.0, "criticality": 1.0}]


def test_live_dep_forwards_and_status_is_current(live_server, tmp_path: Path):
    server, port, server_dir = live_server
    agent_dir = _agent_dir(tmp_path)
    res = DecisionRadarBot(cwd=agent_dir).add_task_dependency("x", "y")
    assert res["remote_sync"]["synced"] is True

    status = get_cruise_server_status(cwd=agent_dir)
    assert status["api_version"] == CRUISE_API_VERSION
    assert status["stale"] is False
    assert status["store_match"] is False
    assert get_cruise_server_status(cwd=server_dir)["store_match"] is True


def test_cli_sync_command(live_server, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    _server, port, _ = live_server
    agent_dir = _agent_dir(tmp_path)
    DecisionRadarBot(cwd=agent_dir).request_decision(decision_id="cli-1", question="q", sync_remote=False)
    monkeypatch.chdir(agent_dir)
    runner = CliRunner()
    text = runner.invoke(decision_cmd, ["sync"])
    assert text.exit_code == 0, text.output
    assert "Synced 1 decisions" in text.output
    as_json = runner.invoke(decision_cmd, ["sync", "--port", str(port), "--json"])
    assert json.loads(as_json.output)["pushed"] == ["cli-1"]
    status = runner.invoke(decision_cmd, ["status"])
    # Rich wraps at terminal width, so compare with whitespace collapsed.
    assert "not this folder" in " ".join(status.output.split())


def test_sync_without_server(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("HATH0R_CRUISE_REMOTE_SYNC", "1")
    res = DecisionRadarBot(cwd=_agent_dir(tmp_path)).sync_store_to_server(port=1)
    assert res["success"] is False
    assert "No Cruise Control server" in res["error"]


def test_detached_spawn_runs_package_entry_point(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    captured = {}

    class _Popen:
        def __init__(self, args, **_kw):
            captured["args"] = args
            self.pid = 4242

    monkeypatch.setenv("HATH0R_TEST_SPAWN_DETACHED", "1")
    monkeypatch.setattr("subprocess.Popen", _Popen)
    _spawn_detached_daemon_process(tmp_path, "127.0.0.1", 1, "Ray")
    module = captured["args"][captured["args"].index("-m") + 1]
    assert module == "hath0r_cli"
    # `python -m <module>` only runs when the module has a __main__ entry point.
    assert importlib.util.find_spec(f"{module}.__main__") is not None


def test_stop_reports_server_it_cannot_stop(stale_server: int, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    from hath0r_cli.server.decision_radar_server import stop_detached_cruise_server

    res = stop_detached_cruise_server(cwd=_agent_dir(tmp_path), port=stale_server)
    assert res["stopped"] is False
    assert "still listening" in res["error"]
    monkeypatch.chdir(tmp_path / "agent")
    out = CliRunner().invoke(decision_cmd, ["stop", "--port", str(stale_server)])
    assert out.exit_code == 1
    assert "still listening" in out.output


def test_status_falls_back_to_default_port_when_saved_server_is_gone(live_server, tmp_path: Path):
    _server, port, _ = live_server
    agent_dir = _agent_dir(tmp_path)
    state_dir = agent_dir / ".hath0r" / "decisions"
    state_dir.mkdir(parents=True)
    (state_dir / "server.json").write_text(json.dumps({"port": 1, "pid": 0, "mode": "stopped"}))
    status = get_cruise_server_status(cwd=agent_dir)
    assert status["port"] == port
    assert status["running"] is True
