"""MCP helpers: group detection, config provisioning, live probes, tool calls and routing."""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from hath0r_cli import mcp


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, body):
        raw = body.encode() if isinstance(body, str) else json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        routes = {"/health": (200, {"status": "healthy"}), "/ready": (503, {}), "/plain": (200, "not json")}
        self._send(*routes.get(self.path, (404, {})))

    def do_POST(self):
        req = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        if self.path == "/bad":
            return self._send(200, "not json")
        if self.path == "/boom":
            return self._send(500, {})
        if req["method"] == "tools/list":
            return self._send(200, {"result": {"tools": [{"name": "kb_search"}, {"nameless": 1}]}})
        name = req["params"]["name"]
        results = {
            "err": {"error": {"code": -1}},
            "scalar": {"result": 3},
            "vote_source_list": {"result": {"content": [{"text": "nope"}, {"text": '{"sources": [1]}'}]}},
            "vote_source_test": {"result": {"isError": True, "content": [{"text": "source down"}]}},
            "vote_source_fetch_sample": {"result": {"content": [{"text": "[1]"}]}},
        }
        self._send(200, results.get(name, {"result": {"ok": True}}))


@pytest.fixture
def server(monkeypatch):
    for var in ("HTTP_PROXY", "http_proxy", "HTTPS_PROXY", "https_proxy", "ALL_PROXY", "all_proxy"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("NO_PROXY", "*")
    httpd = HTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}"
    httpd.shutdown()


@pytest.fixture
def config(tmp_path, monkeypatch, server):
    cfg = tmp_path / "mcp.json"
    cfg.write_text(
        json.dumps(
            {
                "servers": [
                    {"id": "local", "name": "Local", "scope": "project", "base_url": server},
                    {"id": "1-nation-mcp", "name": "1N", "scope": "group", "base_url": server},
                ]
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("HATH0R_MCP_CONFIG", str(cfg))
    return cfg


def test_probe_states(server):
    ok = mcp.check_mcp_connection({"id": "a", "base_url": server, "ready_endpoint": "/ready"})
    assert ok.state == "ok" and ok.tools == ["kb_search"] and ok.ready is False
    degraded = mcp.check_mcp_connection({"id": "b", "base_url": server, "mcp_endpoint": "/boom"})
    assert degraded.state == "degraded" and "HTTP 500" in degraded.error
    bad_json = mcp.check_mcp_connection({"id": "c", "base_url": server, "mcp_endpoint": "/bad"})
    assert bad_json.state == "degraded"
    down = mcp.check_mcp_connection({"id": "d", "base_url": server, "health_endpoint": "/missing"})
    assert down.state == "unreachable"
    assert mcp._http_get(f"{server}/plain") == (200, None, None)
    assert mcp._http_get("http://127.0.0.1:1/x", timeout=0.5)[0] == 0
    assert mcp._http_jsonrpc("http://127.0.0.1:1/x", "tools/list", timeout=0.5)[0] == 0


def test_stdio_probe(tmp_path):
    assert mcp.check_mcp_connection({"id": "s", "transport": "stdio", "command": "sh"}).state == "connected"
    missing = mcp.check_mcp_connection({"id": "s", "transport": "stdio", "command": "no-such-binary-x"})
    assert missing.state == "unreachable"


def test_tool_calls(config):
    assert [s.state for s in mcp.check_all_mcp_connections()] == ["ok", "ok"]
    assert mcp.call_mcp_tool("local", "anything") == {"ok": True}
    assert mcp.call_mcp_tool("Local", "scalar") == {"result": 3}
    with pytest.raises(RuntimeError, match="MCP Tool error"):
        mcp.call_mcp_tool("local", "err")
    with pytest.raises(ValueError, match="Unknown MCP server"):
        mcp.call_mcp_tool("ghost", "x")
    assert mcp.call_vote_source_operation("list") == {"sources": [1]}
    with pytest.raises(RuntimeError, match="source down"):
        mcp.call_vote_source_operation("test", "s1")
    with pytest.raises(RuntimeError, match="JSON object"):
        mcp.call_vote_source_operation("fetch_sample", "s1")
    with pytest.raises(ValueError, match="requires a source ID"):
        mcp.call_vote_source_operation("test")
    with pytest.raises(ValueError, match="Unknown vote-source"):
        mcp.call_vote_source_operation("drop")


def test_tool_result_decoding():
    with pytest.raises(RuntimeError, match="did not contain content"):
        mcp._mcp_tool_data({})
    assert mcp._mcp_tool_message({}) is None
    assert mcp._mcp_tool_message({"content": [1, {"text": "x" * 600}]}) == "x" * 500
    assert mcp._mcp_tool_message({"content": [{"text": 3}]}) is None


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("Books", "author"),
        ("1nation", "1-nation"),
        ("Ray Bayly", "ray"),
        ("websites", "bai"),
        ("x", "hath0r-opensource"),
    ],
    ids=["author", "1n", "ray", "bai", "default"],
)
def test_normalize_group(raw, expected):
    assert mcp.normalize_mcp_group(raw) == expected


@pytest.mark.parametrize(
    "parts,agents,expected",
    [
        (("author",), None, "author"),
        (("1-nation",), None, "1-nation"),
        (("ray",), None, "ray"),
        (("websites",), None, "bai"),
        (("hath0r",), None, "hath0r-opensource"),
        (("plain",), "group `books`", "author"),
        (("plain",), "group: 1-nation", "1-nation"),
        (("plain",), "mcp.raymondbayly.com", "ray"),
        (("plain",), "mcp.baylyai.com", "bai"),
        (("plain",), "mcp.hath0r-cli.com", "hath0r-opensource"),
        (("plain",), "nothing", "hath0r-opensource"),
    ],
    ids=lambda v: v if isinstance(v, str) else None,
)
def test_detect_group(tmp_path_factory, parts, agents, expected):
    root = tmp_path_factory.mktemp("g").joinpath(*parts, "repo")
    root.mkdir(parents=True)
    if agents:
        (root / "AGENTS.md").write_text(agents, encoding="utf-8")
    if "plain" in parts and any(p in str(root).lower().split("/") for p in ("ray", "bai", "author", "hath0r")):
        pytest.skip("temp path contains a group keyword")
    assert mcp.detect_repo_mcp_group(root) == expected


def test_ensure_configs(tmp_path):
    repo = tmp_path / "ws" / "svc"
    (repo / ".git").mkdir(parents=True)
    (repo / "cfg").mkdir()
    (repo / "cfg" / "mcp.servers.json").write_text(
        json.dumps({"description": "mine", "servers": [{"id": "extra", "name": "Extra"}]}), encoding="utf-8"
    )
    dry = mcp.ensure_repo_mcp_config(repo, group="bai", dry_run=True)
    assert dry["cfg_synced"] and not (repo / ".hath0r" / "mcp.json").exists()
    live = mcp.ensure_repo_mcp_config(repo, group="bai")
    assert live["group"] == "bai" and (repo / ".hath0r" / "mcp.json").is_file()
    synced = json.loads((repo / "cfg" / "mcp.servers.json").read_text(encoding="utf-8"))
    assert synced["servers"][-1]["id"] == "extra" and synced["description"] == "mine"
    (repo / "cfg" / "mcp.servers.json").write_text("{broken", encoding="utf-8")
    assert mcp.ensure_repo_mcp_config(repo)["cfg_synced"] is False

    (tmp_path / "ws" / "node_modules" / "dep" / ".git").mkdir(parents=True)
    every = mcp.ensure_all_repos_mcp_config(tmp_path / "ws", dry_run=True)
    assert every["repos_count"] == 1 and every["repos"][0]["repo"] == "svc"
    assert mcp.ensure_all_repos_mcp_config(repo, dry_run=True)["repos"][0]["repo"] == "svc"


def test_validate_config_variants(tmp_path):
    def write(name, text):
        p = tmp_path / name
        p.write_text(text, encoding="utf-8")
        return mcp.validate_mcp_config(p)

    assert write("a.json", "{bad")[0] is False
    assert write("b.yaml", "servers: [unclosed")[0] is False
    assert write("c.json", '{"servers": [1]}')[0] is False
    assert write("d.json", '{"servers": [{"id": "x"}]}')[0] is False
    assert write("e.json", "[]")[0] is False
    ok, warning, servers = write("f.yaml", "servers:\n  - id: g\n    name: G\n    scope: group\n")
    assert ok and "No enabled 'project'" in warning and servers[0]["id"] == "g"
    assert mcp.validate_mcp_config(tmp_path / "missing.json")[0] is False


def test_sort_and_router():
    servers = [
        {"id": "b", "scope": "org"},
        {"id": "a", "scope": "project", "priority": "x"},
        {"id": "c", "scope": "weird", "priority": 1},
    ]
    assert [s["id"] for s in mcp.sort_mcp_servers_by_priority(servers)] == ["a", "b", "c"]

    tools = [
        {
            "name": "kb_search",
            "description": "Search the knowledge base " * 20,
            "inputSchema": {
                "type": "object",
                "required": ["query"],
                "properties": {
                    "query": {"type": "string", "description": "text"},
                    "mode": {"type": "string", "enum": ["a", "b"], "default": "a"},
                    "filters": {"type": "object", "properties": {"tag": {"type": "string"}}},
                    "junk": 3,
                },
            },
        },
        {"name": "voice_speak", "description": "Speak text aloud", "parameters": {"properties": {"text": {}}}},
        {"name": "", "description": ""},
    ]
    router = mcp.DynamicToolRouter()
    assert router.route("anything") == []
    for t in tools:
        router.add_tool(t)
    top = router.route("search knowledge query", top_k=1)
    assert top[0]["name"] == "kb_search" and top[0]["parameters"]["properties"]["filters"]["properties"]
    assert len(top[0]["description"]) <= 120
    raw = router.route("speak", prune=False, threshold=0.1)
    assert raw[0]["name"] == "voice_speak"
    verbose = mcp.SchemaPruner(strip_titles=False).prune(tools[0])
    assert verbose["parameters"]["properties"]["query"]["description"] == "text"
    assert mcp.SchemaPruner().prune("not a dict") == "not a dict"
    assert router.score_tool(set(), tools[0]) == 0.0
