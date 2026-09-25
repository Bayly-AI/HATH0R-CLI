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
# Project MCP (hath0r-mcp) is always priority 1.
DEFAULT_MCP_SERVERS = [
    {
        "id": "hath0r-mcp",
        "name": "Hath0rMCP",
        "scope": "project",
        "group": "hath0r-opensource",
        "priority": 1,
        "product_id": "hath0r-mcp",
        "transport": "streamable-http",
        "base_url": "http://127.0.0.1:38083",
        "mcp_endpoint": "/mcp",
        "health_endpoint": "/health",
        "ready_endpoint": "/ready",
        "description": "Hath0r OpenSource Suite MCP knowledge server and tools (Project MCP)",
        "enabled": True,
        "local_path": "/Users/raybayly/Development/OpenSource/hath0r-mcp",
        "github": "Bayly-AI/HATH0R-MCP",
    },
    {
        "id": "bai-mcp",
        "name": "BaylyAIMCP",
        "scope": "org",
        "group": "bai",
        "priority": 2,
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
        "scope": "group",
        "group": "1-nation",
        "priority": 3,
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


SCOPE_ORDER = {
    "project": 0,
    "group": 1,
    "org": 2,
    "user": 3,
}


def sort_mcp_servers_by_priority(servers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Sort MCP servers ensuring project MCP is always priority 1, followed by group and org.

    Ordering rule (CRITICAL — cr-mcp-priority-001):
    1. Scope: project (rank 0), group (rank 1), org (rank 2), user (rank 3), other (rank 4).
    2. Numerical priority: integer ascending (lower number = higher priority).
    3. Server ID: alphabetical tie-breaker.
    """

    def _sort_key(s: dict[str, Any]) -> tuple[int, int, str]:
        scope = str(s.get("scope", "group")).lower()
        scope_rank = SCOPE_ORDER.get(scope, 4)
        try:
            priority = int(s.get("priority", 100))
        except (ValueError, TypeError):
            priority = 100
        server_id = str(s.get("id", ""))
        return (scope_rank, priority, server_id)

    return sorted(servers, key=_sort_key)


def resolve_mcp_config_path(group_root: Path | None = None) -> Path | None:
    """Locate the MCP connections configuration JSON or YAML file."""
    env_override = os.environ.get("HATH0R_MCP_CONFIG")
    if env_override:
        p = Path(env_override).expanduser()
        if p.is_file():
            return p

    repo_root = Path(__file__).resolve().parents[2]

    # JSON configs take precedence (canonical per cr-mcp-priority-001)
    candidates: list[Path] = [
        repo_root / "cfg" / "mcp.servers.json",
        repo_root / ".hath0r" / "mcp.servers.json",
    ]
    if group_root:
        candidates.extend(
            [
                group_root / "HATH0R-CLI" / "cfg" / "mcp.servers.json",
                group_root / "hathor-cli" / "cfg" / "mcp.servers.json",
                group_root / "cfg" / "mcp.servers.json",
                group_root / "HATH0R-CLI" / "cfg" / "mcp-connections.yaml",
                group_root / "hathor-cli" / "cfg" / "mcp-connections.yaml",
                group_root / "cfg" / "mcp-connections.yaml",
            ]
        )

    candidates.append(repo_root / "cfg" / "mcp-connections.yaml")

    for c in candidates:
        if c.is_file():
            return c
    return None


def validate_mcp_config(config_path: Path) -> tuple[bool, str | None, list[dict[str, Any]]]:
    """Validate MCP configuration file syntax and semantics.

    Returns (is_valid, warning_or_error, sorted_servers).
    """
    if not config_path.is_file():
        return False, f"Config file not found: {config_path}", []

    raw = config_path.read_text(encoding="utf-8")
    data: Any = None
    if config_path.suffix == ".json":
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            return False, f"Invalid JSON syntax in {config_path.name}: {exc}", []
    elif yaml:
        try:
            data = yaml.safe_load(raw)
        except Exception as exc:
            return False, f"Invalid YAML syntax in {config_path.name}: {exc}", []
    else:
        return False, f"Unsupported config format for {config_path.name}", []

    if not isinstance(data, dict) or "servers" not in data or not isinstance(data["servers"], list):
        return False, f"Missing or invalid 'servers' list in {config_path.name}", []

    servers: list[dict[str, Any]] = []
    for s in data["servers"]:
        if not isinstance(s, dict):
            return False, f"Non-object entry in {config_path.name} 'servers' list", []
        if "id" not in s or "name" not in s:
            return False, f"Server entry missing required 'id' or 'name' in {config_path.name}", []
        servers.append(s)

    sorted_servers = sort_mcp_servers_by_priority(servers)
    has_project = any(str(s.get("scope", "")).lower() == "project" and s.get("enabled", True) for s in sorted_servers)
    warning = None
    if not has_project:
        warning = f"Warning: No enabled 'project' scope MCP server defined in {config_path.name}."

    return True, warning, sorted_servers


def load_mcp_connections(group_root: Path | None = None) -> list[dict[str, Any]]:
    """Load configured MCP servers from JSON or YAML, sorted with project MCP first."""
    cfg_path = resolve_mcp_config_path(group_root)
    if cfg_path:
        is_valid, _msg, servers = validate_mcp_config(cfg_path)
        if is_valid and servers:
            return servers
    return sort_mcp_servers_by_priority(list(DEFAULT_MCP_SERVERS))


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



VOTE_SOURCE_TOOL_NAMES = {
    "list": "vote_source_list",
    "test": "vote_source_test",
    "fetch_sample": "vote_source_fetch_sample",
}

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


def call_vote_source_operation(
    operation: str,
    source_id: str | None = None,
    *,
    server_id: str = "1-nation-mcp",
    group_root: Path | None = None,
    timeout: float = 20.0,
) -> dict[str, Any]:
    """Call one bounded vote-source operation through the configured 1N-MCP server."""
    tool_name = VOTE_SOURCE_TOOL_NAMES.get(operation)
    if tool_name is None:
        raise ValueError(f"Unknown vote-source operation: {operation}")
    if operation == "list":
        arguments: dict[str, Any] = {}
    elif source_id:
        arguments = {"source_id": source_id}
    else:
        raise ValueError(f"Vote-source operation '{operation}' requires a source ID")

    result = call_mcp_tool(
        server_id,
        tool_name,
        arguments=arguments,
        group_root=group_root,
        timeout=timeout,
    )
    if result.get("isError"):
        raise RuntimeError(_mcp_tool_message(result) or "Vote-source MCP tool returned an error")
    return _mcp_tool_data(result)


def _mcp_tool_data(result: dict[str, Any]) -> dict[str, Any]:
    """Decode FastMCP text content into a structured result without guessing."""
    content = result.get("content")
    if not isinstance(content, list):
        raise RuntimeError("MCP tool response did not contain content")
    for block in content:
        if not isinstance(block, dict) or not isinstance(block.get("text"), str):
            continue
        try:
            decoded = json.loads(block["text"])
        except json.JSONDecodeError:
            continue
        if isinstance(decoded, dict):
            return decoded
    raise RuntimeError("MCP tool response did not contain a JSON object")


def _mcp_tool_message(result: dict[str, Any]) -> str | None:
    """Extract a safe human-readable tool error without exposing raw transport data."""
    content = result.get("content")
    if not isinstance(content, list):
        return None
    for block in content:
        if isinstance(block, dict):
            text = block.get("text")
            if isinstance(text, str):
                return text[:500]
    return None
