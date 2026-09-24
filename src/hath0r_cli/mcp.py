"""Model Context Protocol (MCP) connection management and verification for Hath0r CLI."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore[assignment]


# Default connection specifications for BaylyAI, 1-Nation, and Hath0r MCP servers.
DEFAULT_MCP_SERVERS = [
    {
        "id": "hath0r-mcp",
        "name": "Hath0rMCP",
        "group": "hath0r-opensource",
        "product_id": "hath0r-mcp",
        "transport": "streamable-http",
        "base_url": "http://127.0.0.1:38083",
        "mcp_endpoint": "/mcp",
        "health_endpoint": "/health",
        "ready_endpoint": "/ready",
        "description": "Hath0r OpenSource Suite MCP knowledge server and tools",
        "enabled": True,
        "local_path": "/Users/raybayly/Development/OpenSource/hath0r-mcp",
        "github": "Bayly-AI/HATH0R-MCP",
    },
    {
        "id": "bai-mcp",
        "name": "BaylyAIMCP",
        "group": "bai",
        "product_id": "bai-mcp",
        "transport": "http-jsonrpc",
        "base_url": "http://127.0.0.1:48080",
        "mcp_endpoint": "/mcp",
        "health_endpoint": "/health",
        "ready_endpoint": "/health",
        "description": "Bayly AI Enterprise MCP knowledgebase and runbook engine",
        "enabled": True,
        "local_path": "/Users/raybayly/Development/BAI/MCP",
        "github": "Bayly-AI/BAI-MCP",
    },
    {
        "id": "1-nation-mcp",
        "name": "1-NationMCP",
        "group": "1-nation",
        "product_id": "1-nation-mcp",
        "transport": "streamable-http",
        "base_url": "http://127.0.0.1:58083",
        "mcp_endpoint": "/mcp",
        "health_endpoint": "/health",
        "ready_endpoint": "/ready",
        "description": "1-Nation Suite MCP service and reference tools",
        "enabled": True,
        "local_path": "/Users/raybayly/Development/1-Nation/MCP",
        "github": "Bayly-AI/1-Nation-MCP",
    },
]


@dataclass
class McpConnectionStatus:
    """Status result of an MCP connection check."""

    server_id: str
    name: str
    group: str
    base_url: str
    transport: str
    state: str  # ok | degraded | unreachable
    latency_ms: int
    health_status: str
    ready: bool
    tools_count: int
    tools: list[str] = field(default_factory=list)
    message: str = ""
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def resolve_mcp_config_path(group_root: Path | None = None) -> Path | None:
    """Locate the MCP connections configuration YAML file."""
    env_override = os.environ.get("HATH0R_MCP_CONFIG")
    if env_override:
        p = Path(env_override).expanduser()
        if p.is_file():
            return p

    candidates: list[Path] = []
    if group_root:
        candidates.append(group_root / "HATH0R-CLI" / "cfg" / "mcp-connections.yaml")
        candidates.append(group_root / "hathor-cli" / "cfg" / "mcp-connections.yaml")
        candidates.append(group_root / "cfg" / "mcp-connections.yaml")

    repo_cfg = Path(__file__).resolve().parents[2] / "cfg" / "mcp-connections.yaml"
    candidates.append(repo_cfg)

    for c in candidates:
        if c.is_file():
            return c
    return None


def load_mcp_connections(group_root: Path | None = None) -> list[dict[str, Any]]:
    """Load configured MCP servers from YAML or fallback to default suite servers."""
    cfg_path = resolve_mcp_config_path(group_root)
    if cfg_path and yaml:
        try:
            data = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
            if isinstance(data, dict) and "servers" in data and isinstance(data["servers"], list):
                return data["servers"]
        except Exception:
            pass
    return list(DEFAULT_MCP_SERVERS)


def _http_get(url: str, timeout: float = 2.0) -> tuple[int, dict[str, Any] | None, str | None]:
    """Execute a lightweight HTTP GET request."""
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "hath0r-cli/0.3.0", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            code = resp.getcode()
            body = resp.read().decode("utf-8", errors="replace")
            try:
                data = json.loads(body)
                return code, data, None
            except json.JSONDecodeError:
                return code, None, None
    except urllib.error.HTTPError as e:
        return e.code, None, f"HTTP {e.code}: {e.reason}"
    except Exception as e:
        return 0, None, str(e)


def _http_jsonrpc(
    url: str,
    method: str,
    params: dict[str, Any] | None = None,
    timeout: float = 3.0,
) -> tuple[int, dict[str, Any] | None, str | None]:
    """Send an MCP JSON-RPC 2.0 request."""
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": method,
        "params": params or {},
    }
    data_bytes = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data_bytes,
        headers={
            "User-Agent": "hath0r-cli/0.3.0",
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            code = resp.getcode()
            body = resp.read().decode("utf-8", errors="replace")
            try:
                res_data = json.loads(body)
                return code, res_data, None
            except json.JSONDecodeError:
                return code, None, "Invalid JSON in response"
    except urllib.error.HTTPError as e:
        return e.code, None, f"HTTP {e.code}: {e.reason}"
    except Exception as e:
        return 0, None, str(e)


def check_mcp_connection(server: dict[str, Any], timeout: float = 2.5) -> McpConnectionStatus:
    """Verify live connectivity, health, readiness, and MCP tools discovery."""
    server_id = server.get("id", "unknown")
    name = server.get("name", server_id)
    group = server.get("group", "")
    base_url = server.get("base_url", "").rstrip("/")
    transport = server.get("transport", "http")

    health_ep = server.get("health_endpoint", "/health")
    ready_ep = server.get("ready_endpoint", health_ep)
    mcp_ep = server.get("mcp_endpoint", "/mcp")

    health_url = f"{base_url}{health_ep}"
    ready_url = f"{base_url}{ready_ep}"
    mcp_url = f"{base_url}{mcp_ep}"

    start = time.perf_counter()

    # 1. Health check
    h_code, h_data, h_err = _http_get(health_url, timeout=timeout)
    if h_code != 200:
        latency = int((time.perf_counter() - start) * 1000)
        return McpConnectionStatus(
            server_id=server_id,
            name=name,
            group=group,
            base_url=base_url,
            transport=transport,
            state="unreachable",
            latency_ms=latency,
            health_status="unreachable",
            ready=False,
            tools_count=0,
            tools=[],
            message=f"Health probe failed: {h_err or f'HTTP {h_code}'}",
            error=h_err or f"HTTP {h_code}",
        )

    health_status = "healthy"
    if isinstance(h_data, dict):
        health_status = str(h_data.get("status", "healthy"))

    # 2. Readiness probe (if distinct)
    ready = True
    if ready_ep != health_ep:
        r_code, _, _ = _http_get(ready_url, timeout=timeout)
        ready = (r_code == 200)

    # 3. MCP JSON-RPC tools/list
    m_code, m_data, m_err = _http_jsonrpc(mcp_url, "tools/list", timeout=timeout)
    latency = int((time.perf_counter() - start) * 1000)

    tools: list[str] = []
    if m_code == 200 and isinstance(m_data, dict):
        result = m_data.get("result", {})
        raw_tools = result.get("tools", [])
        if isinstance(raw_tools, list):
            for t in raw_tools:
                if isinstance(t, dict) and "name" in t:
                    tools.append(t["name"])
        state = "ok"
        msg = f"Connected successfully ({len(tools)} tools available, {latency}ms)"
        err = None
    else:
        state = "degraded"
        msg = f"Health OK but MCP tools/list failed: {m_err or f'HTTP {m_code}'}"
        err = m_err or f"HTTP {m_code}"

    return McpConnectionStatus(
        server_id=server_id,
        name=name,
        group=group,
        base_url=base_url,
        transport=transport,
        state=state,
        latency_ms=latency,
        health_status=health_status,
        ready=ready,
        tools_count=len(tools),
        tools=tools,
        message=msg,
        error=err,
    )


def check_all_mcp_connections(
    group_root: Path | None = None,
    timeout: float = 2.5,
) -> list[McpConnectionStatus]:
    """Probe all configured MCP connections."""
    servers = load_mcp_connections(group_root)
    results: list[McpConnectionStatus] = []
    for s in servers:
        if s.get("enabled", True):
            results.append(check_mcp_connection(s, timeout=timeout))
    return results


def call_mcp_tool(
    server_id: str,
    tool_name: str,
    arguments: dict[str, Any] | None = None,
    group_root: Path | None = None,
    timeout: float = 5.0,
) -> dict[str, Any]:
    """Execute a tool on a specific MCP server via JSON-RPC."""
    servers = load_mcp_connections(group_root)
    server = next((s for s in servers if s.get("id") == server_id or s.get("name") == server_id), None)
    if not server:
        raise ValueError(f"Unknown MCP server '{server_id}'. Available: {[s.get('id') for s in servers]}")

    base_url = server.get("base_url", "").rstrip("/")
    mcp_url = f"{base_url}{server.get('mcp_endpoint', '/mcp')}"

    params = {
        "name": tool_name,
        "arguments": arguments or {},
    }
    code, data, err = _http_jsonrpc(mcp_url, "tools/call", params=params, timeout=timeout)
    if code != 200 or not isinstance(data, dict):
        raise RuntimeError(f"Tool call failed on {server_id}: {err or f'HTTP {code}'}")

    if "error" in data:
        error_info = data["error"]
        raise RuntimeError(f"MCP Tool error ({server_id}): {error_info}")

    result = data.get("result", {})
    return result if isinstance(result, dict) else {"result": result}
