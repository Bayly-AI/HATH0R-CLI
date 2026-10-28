"""CLI tests for `hath0r mcp` subcommands with network, Docker and config writes mocked out."""

from __future__ import annotations

import json
from dataclasses import dataclass, field

import pytest
from click.testing import CliRunner

import hath0r_cli.bots.sibling_bot as sibling_bot
import hath0r_cli.mcp as mcp_mod
import hath0r_cli.server.mcp_server as mcp_server
from hath0r_cli.cli import main


def _run(*args: str, input: str | None = None):
    return CliRunner().invoke(main, list(args), input=input)


@pytest.mark.parametrize(
    "args, result, code",
    [
        (["mcp", "sources", "list"], {"state": "ok", "sources": []}, 0),
        (["mcp", "sources", "test", "fec"], {"state": "credential_required"}, 0),
        (["mcp", "sources", "fetch-sample", "fec"], {"state": "upstream_error"}, 6),
    ],
)
def test_mcp_sources(monkeypatch, args, result, code):
    monkeypatch.setattr(mcp_mod, "call_vote_source_operation", lambda *a, **k: result)
    res = _run("-o", "text", *args)
    assert res.exit_code == code, res.output
    assert result["state"] in res.output


def test_mcp_sources_call_failure(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("server down")

    monkeypatch.setattr(mcp_mod, "call_vote_source_operation", boom)
    res = _run("-o", "json", "mcp", "sources", "list")
    assert res.exit_code == 1
    assert "VOTE_SOURCE_MCP_CALL_FAILED" in res.output


def test_mcp_list_text(monkeypatch):
    servers = [{"id": "a", "name": "A", "enabled": True}, {"id": "b", "name": "B", "enabled": False}]
    monkeypatch.setattr(mcp_mod, "load_mcp_connections", lambda root: servers)
    res = _run("-o", "text", "mcp", "list")
    assert res.exit_code == 0 and "Configured MCP Servers" in res.output


def test_mcp_init_and_ensure_all_text(monkeypatch, tmp_path):
    monkeypatch.setattr(
        mcp_mod,
        "ensure_repo_mcp_config",
        lambda *a, **k: {"success": True, "mcp_file": "x/.hath0r/mcp.json", "group": "bai",
                         "default_server": "bai-mcp", "default_url": "http://h"},
    )
    res = _run("-o", "text", "mcp", "init", "--dry-run")
    assert res.exit_code == 0 and "Provisioned canonical" in res.output

    monkeypatch.setattr(
        mcp_mod,
        "ensure_all_repos_mcp_config",
        lambda *a, **k: {"success": True, "repos_count": 2,
                         "repos": [{"repo": "r1", "mcp_not_ignored": True}, {"repo": "r2", "mcp_not_ignored": False}]},
    )
    res = _run("-o", "text", "mcp", "ensure-all", "--root", str(tmp_path), "--dry-run")
    assert res.exit_code == 0 and "Fleet Provisioning" in res.output


@dataclass
class _Check:
    name: str
    state: str
    message: str = ""
    server_id: str = "s"
    base_url: str = "http://h"
    latency_ms: int = 3
    tools_count: int = 2
    extra: dict = field(default_factory=dict)

    def to_dict(self):
        return {"name": self.name, "state": self.state}


@pytest.mark.parametrize(
    "states, code, fragment",
    [
        (["ok"], 0, "All MCP connections active"),
        (["ok", "degraded"], 0, "degraded or unreachable"),
        (["error"], 6, "UNREACHABLE"),
    ],
)
def test_mcp_check(monkeypatch, states, code, fragment):
    results = [_Check(name=f"s{i}", state=s, message="refused") for i, s in enumerate(states)]
    monkeypatch.setattr(mcp_mod, "check_all_mcp_connections", lambda **k: results)
    res = _run("-o", "text", "mcp", "check")
    assert res.exit_code == code, res.output
    assert fragment in res.output


def test_mcp_call(monkeypatch):
    monkeypatch.setattr(mcp_mod, "call_mcp_tool", lambda *a, **k: {"answer": 42})
    res = _run("-o", "text", "mcp", "call", "srv", "tool", "--args", '{"q": 1}')
    assert res.exit_code == 0 and "42" in res.output

    def boom(*a, **k):
        raise RuntimeError("tool exploded")

    monkeypatch.setattr(mcp_mod, "call_mcp_tool", boom)
    assert _run("-o", "json", "mcp", "call", "srv", "tool").exit_code == 1
    assert _run("-o", "json", "mcp", "call", "srv", "tool", "--args", "{bad").exit_code == 2


def test_mcp_route_text():
    res = _run("-o", "text", "mcp", "route", "--intent", "create a pull request", "--top-k", "2")
    assert res.exit_code == 0 and "tools matching" in res.output


def test_mcp_prune(tmp_path):
    schema = {"name": "t", "description": "A tool. " * 20, "parameters": {"type": "object", "properties": {}}}
    single = tmp_path / "one.json"
    single.write_text(json.dumps(schema), encoding="utf-8")
    many = tmp_path / "many.json"
    many.write_text(json.dumps([schema, schema]), encoding="utf-8")
    bad = tmp_path / "bad.json"
    bad.write_text("{nope", encoding="utf-8")

    assert "reduction" in _run("-o", "text", "mcp", "prune", str(single)).output
    assert json.loads(_run("-o", "json", "mcp", "prune", str(many)).output)["command"] == "mcp.prune"
    assert _run("-o", "json", "mcp", "prune", str(bad)).exit_code == 2


def test_mcp_connect(monkeypatch):
    import hath0r_cli.mcp_security as sec

    class Mgr:
        def __init__(self, ok):
            self.ok = ok

        def connect_server(self, **kw):
            assert kw["env"] == {"A": "1"}
            return {"success": True} if self.ok else {"success": False, "error": "bad command"}

    for ok, fragment in ((True, "Dynamically Mounted"), (False, "bad command")):
        monkeypatch.setattr(sec, "DynamicMCPManager", lambda ok=ok: Mgr(ok))
        res = _run("-o", "text", "mcp", "connect", "srv", "--command", "npx srv", "-e", "A=1", "-e", "junk")
        assert fragment in res.output


def test_mcp_inspect_and_policy():
    allowed = _run("-o", "text", "mcp", "inspect", "-s", "fs", "-t", "read", "-a", '{"path": "README.md"}')
    assert "ALLOWED" in allowed.output
    blocked = _run("-o", "text", "mcp", "inspect", "-s", "sh", "-t", "run", "-a", '{"cmd": "git push origin main --force"}')
    assert "BLOCKED" in blocked.output
    assert _run("-o", "text", "mcp", "inspect", "-s", "a", "-t", "b", "-a", "{bad").exit_code == 2
    policy = _run("-o", "text", "mcp", "policy", "list")
    assert policy.exit_code == 0 and "MCP Security Guardrails" in policy.output


def test_mcp_serve(monkeypatch):
    monkeypatch.setattr(
        mcp_server,
        "install_claude_desktop_connector",
        lambda **k: {"config_path": "/c.json", "server_name": "hath0r-cli", "command": "hath0r", "args": ["mcp", "serve"]},
    )
    res = _run("-o", "text", "mcp", "serve", "--install-claude-only")
    assert res.exit_code == 0 and "Registered with Claude Desktop" in res.output

    class Server:
        def run(self, transport):
            raise RuntimeError("port busy")

    monkeypatch.setattr(mcp_server, "create_mcp_server", lambda: Server())
    res = _run("-o", "json", "mcp", "serve", "--install-claude", "--transport", "sse")
    assert res.exit_code == 1 and "MCP_SERVER_ERROR" in res.output


class _Sibling:
    install = {"success": True, "name": "hath0r-mcp", "path": "/p", "version": "1.0", "installed_deps": True}
    container = {"success": True, "source": "remote_url", "container_name": "c", "container_url": "u", "status": "up"}

    def download_and_install(self, *a, **k):
        return dict(self.install)

    def install_container(self, *a, **k):
        return dict(self.container)


@pytest.mark.parametrize(
    "install, container, args, code, fragment",
    [
        (_Sibling.install, _Sibling.container, ["--container", "--image-url", "u"], 0, "Container deployed"),
        ({**_Sibling.install, "already_installed": True}, None, [], 0, "Already installed"),
        (_Sibling.install, {"success": False, "error": "docker down"}, ["--container", "--no-prompt"], 1, "docker down"),
        ({"success": False, "error": "no network"}, None, [], 1, "MCP_INSTALL_FAILED"),
    ],
)
def test_mcp_install(monkeypatch, install, container, args, code, fragment):
    bot = _Sibling()
    bot.install = install
    bot.container = container or _Sibling.container
    monkeypatch.setattr(sibling_bot, "SiblingManagerBot", lambda: bot)
    mode = "json" if "MCP_" in fragment else "text"
    res = _run("-o", mode, "mcp", "install", *args)
    assert res.exit_code == code, res.output
    assert fragment in res.output


@pytest.mark.parametrize(
    "container, code, fragment",
    [
        ({"success": True, "dry_run": True, "action": "would run"}, 0, "DRY-RUN"),
        ({"success": True, "source": "local", "container_name": "c", "container_url": "u", "status": "up"}, 0, "local git"),
        ({"success": False, "error": "no docker"}, 1, "no docker"),
    ],
)
def test_mcp_container(monkeypatch, container, code, fragment):
    bot = _Sibling()
    bot.container = container
    monkeypatch.setattr(sibling_bot, "SiblingManagerBot", lambda: bot)
    res = _run("-o", "text", "mcp", "container", "--no-prompt", "--dry-run")
    assert res.exit_code == code, res.output
    assert fragment in res.output
