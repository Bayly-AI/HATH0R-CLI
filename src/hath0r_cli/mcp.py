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


# Canonical Hath0r MCP servers across the four organizational groups.
# Every group MCP server is powered by the Hath0r MCP engine (streamable-http at /mcp).
CANONICAL_HATH0R_MCP_SERVERS: list[dict[str, Any]] = [
    {
        "id": "hath0r-mcp",
        "name": "Hath0rMCP",
        "engine": "hath0r-mcp",
        "scope": "project",
        "group": "hath0r-opensource",
        "priority": 1,
        "product_id": "hath0r-mcp",
        "transport": "streamable-http",
        "base_url": "https://mcp.hath0r-cli.com",
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
        "engine": "hath0r-mcp",
        "scope": "org",
        "group": "bai",
        "priority": 2,
        "product_id": "bai-mcp",
        "transport": "streamable-http",
        "base_url": "https://mcp.baylyai.com",
        "mcp_endpoint": "/mcp",
        "health_endpoint": "/health",
        "ready_endpoint": "/ready",
        "description": "Bayly AI Enterprise Hath0r MCP knowledgebase and runbook engine",
        "enabled": True,
        "local_path": "/Users/raybayly/Development/BAI/MCP",
        "github": "Bayly-AI/BAI-MCP",
    },
    {
        "id": "ray-mcp",
        "name": "RayMCP",
        "engine": "hath0r-mcp",
        "scope": "group",
        "group": "ray",
        "priority": 3,
        "product_id": "ray-mcp",
        "transport": "streamable-http",
        "base_url": "https://mcp.raymondbayly.com",
        "mcp_endpoint": "/mcp",
        "health_endpoint": "/health",
        "ready_endpoint": "/ready",
        "description": "Ray Bayly Hath0r MCP knowledgebase and executive tools",
        "enabled": True,
        "local_path": "/Users/raybayly/Development/Ray/mcp",
        "github": "Bayly-AI/RAY-MCP",
    },
    {
        "id": "1-nation-mcp",
        "name": "1-NationMCP",
        "engine": "hath0r-mcp",
        "scope": "group",
        "group": "1-nation",
        "priority": 4,
        "product_id": "1-nation-mcp",
        "transport": "streamable-http",
        "base_url": "https://mcp.1-nation.com",
        "mcp_endpoint": "/mcp",
        "health_endpoint": "/health",
        "ready_endpoint": "/ready",
        "description": "1-Nation Suite Hath0r MCP service and reference tools",
        "enabled": True,
        "local_path": "/Users/raybayly/Development/1-Nation/MCP",
        "github": "Bayly-AI/1-Nation-MCP",
    },
    {
        "id": "author-mcp",
        "name": "AuthorMCP",
        "engine": "author-mcp",
        "scope": "project",
        "group": "author",
        "priority": 5,
        "product_id": "author-mcp",
        "transport": "streamable-http",
        "base_url": "http://127.0.0.1:18083",
        "mcp_endpoint": "/mcp",
        "health_endpoint": "/health",
        "ready_endpoint": "/ready",
        "description": "Author MCP root knowledge server, Air Traffic Control (ATC), and tools for Author project",
        "enabled": True,
        "local_path": "/Users/raybayly/Development/Projects/Author/mcp",
        "github": "somesayray/author-mcp",
    },
]

# Default connection specifications for BaylyAI, Ray, 1-Nation, and Hath0r MCP servers.
DEFAULT_MCP_SERVERS: list[dict[str, Any]] = [
    *CANONICAL_HATH0R_MCP_SERVERS,
    {
        "id": "paper-design-mcp",
        "name": "PaperDesignMCP",
        "scope": "tools",
        "group": "design",
        "priority": 5,
        "product_id": "paper-design-mcp",
        "transport": "streamable-http",
        "base_url": "http://127.0.0.1:29979",
        "mcp_endpoint": "/mcp",
        "health_endpoint": "/health",
        "ready_endpoint": "/health",
        "command": os.path.expanduser("~/.paper/bin/paper"),
        "command_args": ["mcp"],
        "description": "Paper.design MCP server for bi-directional canvas-to-code and website design",
        "enabled": True,
        "local_path": os.path.expanduser("~/.paper"),
        "github": "paper-design/agent-plugins",
        "docs_url": "https://paper.design",
    },
]

GROUP_DEFAULT_MCP_SERVER: dict[str, dict[str, str]] = {
    "hath0r-opensource": {
        "server_id": "hath0r-mcp",
        "name": "Hath0rMCP",
        "base_url": "https://mcp.hath0r-cli.com",
        "mcp_endpoint": "/mcp",
    },
    "bai": {
        "server_id": "bai-mcp",
        "name": "BaylyAIMCP",
        "base_url": "https://mcp.baylyai.com",
        "mcp_endpoint": "/mcp",
    },
    "ray": {
        "server_id": "ray-mcp",
        "name": "RayMCP",
        "base_url": "https://mcp.raymondbayly.com",
        "mcp_endpoint": "/mcp",
    },
    "1-nation": {
        "server_id": "1-nation-mcp",
        "name": "1-NationMCP",
        "base_url": "https://mcp.1-nation.com",
        "mcp_endpoint": "/mcp",
    },
    "author": {
        "server_id": "author-mcp",
        "name": "AuthorMCP",
        "base_url": "http://127.0.0.1:18083",
        "mcp_endpoint": "/mcp",
    },
}


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
    "tools": 3,
    "design": 3,
    "user": 4,
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


def normalize_mcp_group(group: str) -> str:
    """Normalize a repository group identifier into one of the canonical Hath0r MCP groups."""
    g = group.strip().lower()
    if g in {"author", "books"}:
        return "author"
    if g in {"1-nation", "1nation", "one-nation"}:
        return "1-nation"
    if g in {"ray", "ray-bayly", "ray bayly", "raymondbayly"}:
        return "ray"
    if g in {"bai", "bayly-ai", "baylyai", "websites"}:
        return "bai"
    return "hath0r-opensource"


def detect_repo_mcp_group(repo_root: Path) -> str:
    """Detect the canonical Hath0r MCP group for a repository from its path and AGENTS.md metadata."""
    resolved = repo_root.resolve()
    parts_lower = [p.lower() for p in resolved.parts]

    if "author" in parts_lower or "books" in parts_lower:
        return "author"
    if "1-nation" in parts_lower:
        return "1-nation"
    if "ray" in parts_lower or "ray bayly" in parts_lower or resolved.name.lower() in {"ray-mcp", "ray bayly"}:
        return "ray"
    if "bai" in parts_lower or "websites" in parts_lower:
        return "bai"
    if "opensource" in parts_lower or "hath0r" in parts_lower:
        return "hath0r-opensource"

    agents_md = resolved / "AGENTS.md"
    if agents_md.is_file():
        try:
            head = agents_md.read_text(encoding="utf-8", errors="ignore")[:2000].lower()
            if "`author`" in head or "`books`" in head or "role: **books**" in head or "role: **mcp**" in head:
                return "author"
            if "`1-nation`" in head or "group: 1-nation" in head:
                return "1-nation"
            if "`ray`" in head or "mcp.raymondbayly.com" in head:
                return "ray"
            if "`bai`" in head or "mcp.baylyai.com" in head:
                return "bai"
            if "`hath0r-opensource`" in head or "mcp.hath0r-cli.com" in head:
                return "hath0r-opensource"
        except Exception:
            pass

    return "hath0r-opensource"


def build_repo_mcp_config(repo_root: Path, group: str | None = None) -> dict[str, Any]:
    """Build the canonical .hath0r/mcp.json payload for a repository with its group Hath0r MCP as Priority 1."""
    resolved_root = repo_root.resolve()
    resolved_group = normalize_mcp_group(group) if group else detect_repo_mcp_group(resolved_root)
    default_info = GROUP_DEFAULT_MCP_SERVER.get(resolved_group, GROUP_DEFAULT_MCP_SERVER["hath0r-opensource"])
    default_server_id = default_info["server_id"]

    servers: list[dict[str, Any]] = []
    next_priority = 2
    for base_srv in CANONICAL_HATH0R_MCP_SERVERS:
        srv = dict(base_srv)
        srv["engine"] = "hath0r-mcp"
        if srv["id"] == default_server_id:
            srv["scope"] = "project"
            srv["priority"] = 1
        else:
            srv["scope"] = "org" if srv["id"] == "bai-mcp" else "group"
            srv["priority"] = next_priority
            next_priority += 1
        servers.append(srv)

    sorted_servers = sort_mcp_servers_by_priority(servers)
    mcp_servers_map: dict[str, dict[str, Any]] = {}
    for srv in sorted_servers:
        sid = str(srv["id"])
        ep = str(srv.get("mcp_endpoint", "/mcp"))
        url = f"{str(srv['base_url']).rstrip('/')}{ep}"
        mcp_servers_map[sid] = {
            "type": str(srv.get("transport", "streamable-http")),
            "url": url,
            "engine": "hath0r-mcp",
            "group": str(srv.get("group", "")),
            "default": sid == default_server_id,
        }

    return {
        "version": "1.0",
        "engine": "hath0r-mcp",
        "default_provider": "hath0r-mcp",
        "group": resolved_group,
        "default_server": default_server_id,
        "description": f"Canonical Hath0r MCP configuration for {resolved_root.name} (group: {resolved_group})",
        "mcpServers": mcp_servers_map,
        "servers": sorted_servers,
    }


def ensure_repo_mcp_config(
    repo_root: Path,
    group: str | None = None,
    sync_cfg: bool = True,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Ensure <repo_root>/.hath0r/mcp.json exists, uses the group's default Hath0r MCP, and is un-ignored in .gitignore."""
    resolved_root = repo_root.resolve()
    payload = build_repo_mcp_config(resolved_root, group=group)
    mcp_file = resolved_root / ".hath0r" / "mcp.json"
    cfg_file = resolved_root / "cfg" / "mcp.servers.json"

    if not dry_run:
        mcp_file.parent.mkdir(parents=True, exist_ok=True)
        mcp_file.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    cfg_synced = False
    if sync_cfg and cfg_file.is_file():
        try:
            existing = json.loads(cfg_file.read_text(encoding="utf-8"))
            existing_servers = existing.get("servers", []) if isinstance(existing, dict) else []
            canonical_ids = {s["id"] for s in CANONICAL_HATH0R_MCP_SERVERS}
            extra_servers: list[dict[str, Any]] = []
            next_prio = len(payload["servers"]) + 1
            for es in existing_servers:
                if isinstance(es, dict) and es.get("id") not in canonical_ids:
                    es_copy = dict(es)
                    es_copy["priority"] = next_prio
                    next_prio += 1
                    extra_servers.append(es_copy)

            updated_cfg = {
                "version": "1.0",
                "engine": "hath0r-mcp",
                "default_provider": "hath0r-mcp",
                "group": payload["group"],
                "default_server": payload["default_server"],
                "description": existing.get("description", payload["description"])
                if isinstance(existing, dict)
                else payload["description"],
                "servers": [*payload["servers"], *extra_servers],
            }
            if not dry_run:
                cfg_file.write_text(json.dumps(updated_cfg, indent=2) + "\n", encoding="utf-8")
            cfg_synced = True
        except Exception:
            pass

    mcp_not_ignored = True
    try:
        from hath0r_cli.bots.memory_manager import MemoryManagerBot

        mbot = MemoryManagerBot(cwd=resolved_root)
        gi_res = mbot.ensure_gitignore_unignores_graphs(dry_run=dry_run)
        mcp_not_ignored = bool(gi_res.get("graphs_not_ignored", True))
    except Exception:
        pass

    default_srv = payload["servers"][0]
    return {
        "success": True,
        "dry_run": dry_run,
        "repo": resolved_root.name,
        "path": str(resolved_root),
        "mcp_file": str(mcp_file),
        "group": payload["group"],
        "engine": payload["engine"],
        "default_server": payload["default_server"],
        "default_url": default_srv["base_url"],
        "mcp_endpoint": default_srv.get("mcp_endpoint", "/mcp"),
        "cfg_synced": cfg_synced,
        "mcp_not_ignored": mcp_not_ignored,
        "servers_count": len(payload["servers"]),
    }


def ensure_all_repos_mcp_config(
    root_dir: Path | str | None = None,
    sync_cfg: bool = True,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Discover all Git repositories under root_dir and provision canonical .hath0r/mcp.json files."""
    base = Path(root_dir).resolve() if root_dir else Path("/Users/raybayly/Development")
    if not base.is_dir():
        base = Path.cwd().resolve()

    skip_parts = {"node_modules", ".venv", "ARCHIVE", "archive", ".terraform", "__pycache__"}
    repo_paths: list[Path] = []
    if (base / ".git").exists():
        repo_paths.append(base)
    else:
        for git_entry in sorted(base.rglob(".git")):
            if any(p in git_entry.parts for p in skip_parts):
                continue
            repo_paths.append(git_entry.parent)

    results: list[dict[str, Any]] = []
    for rpath in repo_paths:
        res = ensure_repo_mcp_config(rpath, sync_cfg=sync_cfg, dry_run=dry_run)
        res["repo"] = str(rpath.relative_to(base)) if rpath != base else rpath.name
        results.append(res)

    return {
        "success": True,
        "dry_run": dry_run,
        "root_dir": str(base),
        "repos_count": len(results),
        "repos": results,
    }


def resolve_mcp_config_path(group_root: Path | None = None, cwd: Path | None = None) -> Path | None:
    """Locate the MCP connections configuration JSON or YAML file.

    Resolution priority:
    1. HATH0R_MCP_CONFIG environment variable override
    2. <cwd>/.hath0r/mcp.json (canonical per-repo Hath0r MCP config)
    3. <cwd>/cfg/mcp.servers.json
    4. <cwd>/.hath0r/mcp.servers.json
    5. <cli_repo_root>/.hath0r/mcp.json and <cli_repo_root>/cfg/mcp.servers.json
    6. <group_root> fallbacks
    """
    env_override = os.environ.get("HATH0R_MCP_CONFIG")
    if env_override:
        p = Path(env_override).expanduser()
        if p.is_file():
            return p

    active_cwd = (cwd or Path.cwd()).resolve()
    repo_root = Path(__file__).resolve().parents[2]

    candidates: list[Path] = [
        active_cwd / ".hath0r" / "mcp.json",
        active_cwd / "cfg" / "mcp.servers.json",
        active_cwd / ".hath0r" / "mcp.servers.json",
        repo_root / ".hath0r" / "mcp.json",
        repo_root / "cfg" / "mcp.servers.json",
        repo_root / ".hath0r" / "mcp.servers.json",
    ]
    if group_root:
        candidates.extend(
            [
                group_root / "HATH0R-CLI" / ".hath0r" / "mcp.json",
                group_root / "HATH0R-CLI" / "cfg" / "mcp.servers.json",
                group_root / "hathor-cli" / ".hath0r" / "mcp.json",
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


def load_mcp_connections(group_root: Path | None = None, cwd: Path | None = None) -> list[dict[str, Any]]:
    """Load configured MCP servers from JSON or YAML, sorted with project MCP first."""
    cfg_path = resolve_mcp_config_path(group_root=group_root, cwd=cwd)
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

    start = time.perf_counter()

    if transport == "stdio" or not base_url:
        import shutil

        cmd = server.get("command", "")
        binary = shutil.which(cmd) if cmd else None
        if binary or (cmd and Path(cmd).exists()):
            latency = int((time.perf_counter() - start) * 1000)
            return McpConnectionStatus(
                server_id=server_id,
                name=name,
                group=group,
                base_url=base_url,
                transport=transport,
                state="connected",
                latency_ms=latency,
                health_status="healthy",
                ready=True,
                tools_count=1,
                tools=[cmd or name],
                message=f"stdio command binary '{cmd}' verified",
            )
        else:
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
                message=f"stdio command binary '{cmd}' not found",
                error=f"Command '{cmd}' not found in PATH or filesystem",
            )

    health_url = f"{base_url}{health_ep}"
    ready_url = f"{base_url}{ready_ep}"
    mcp_url = f"{base_url}{mcp_ep}"

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
        ready = r_code == 200

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


class SchemaPruner:
    """Compresses verbose JSON Schema tool definitions to reduce prompt context bloat."""

    def __init__(self, max_desc_len: int = 120, strip_titles: bool = True) -> None:
        self.max_desc_len = max_desc_len
        self.strip_titles = strip_titles

    def prune(self, tool_spec: dict[str, Any]) -> dict[str, Any]:
        """Prune tool spec preserving required fields, types, and enums."""
        if not isinstance(tool_spec, dict):
            return tool_spec

        pruned: dict[str, Any] = {
            "name": tool_spec.get("name", ""),
        }

        # Truncate or condense tool description
        desc = tool_spec.get("description", "")
        if desc:
            pruned["description"] = desc[: self.max_desc_len].strip()

        schema = tool_spec.get("inputSchema") or tool_spec.get("parameters") or {}
        if isinstance(schema, dict):
            pruned["parameters"] = self._prune_schema(schema)

        return pruned

    def _prune_schema(self, schema: dict[str, Any]) -> dict[str, Any]:
        out: dict[str, Any] = {"type": schema.get("type", "object")}
        if "required" in schema:
            out["required"] = schema["required"]

        props = schema.get("properties", {})
        if isinstance(props, dict):
            pruned_props = {}
            for k, v in props.items():
                if isinstance(v, dict):
                    prop_entry = {"type": v.get("type", "string")}
                    if "enum" in v:
                        prop_entry["enum"] = v["enum"]
                    if "default" in v:
                        prop_entry["default"] = v["default"]
                    if "description" in v and not self.strip_titles:
                        prop_entry["description"] = v["description"][: self.max_desc_len]
                    if v.get("type") == "object" and "properties" in v:
                        prop_entry["properties"] = self._prune_schema(v).get("properties", {})
                    pruned_props[k] = prop_entry
            out["properties"] = pruned_props
        return out


class DynamicToolRouter:
    """Dynamically routes and filters active tool schemas based on lexical and semantic relevance."""

    def __init__(
        self,
        tools: list[dict[str, Any]] | None = None,
        pruner: SchemaPruner | None = None,
    ) -> None:
        self.tools = tools or []
        self.pruner = pruner or SchemaPruner()

    def add_tool(self, tool: dict[str, Any]) -> None:
        self.tools.append(tool)

    def route(
        self,
        intent: str,
        top_k: int = 5,
        threshold: float = 0.0,
        prune: bool = True,
    ) -> list[dict[str, Any]]:
        """Score and return top-K tool definitions matching task intent."""
        if not self.tools:
            return []

        scored: list[tuple[float, dict[str, Any]]] = []
        intent_tokens = set(intent.lower().replace("_", " ").replace("-", " ").split())

        for tool in self.tools:
            score = self.score_tool(intent_tokens, tool)
            if score >= threshold:
                scored.append((score, tool))

        # Sort descending by score
        scored.sort(key=lambda x: x[0], reverse=True)
        top_tools = [tool for _, tool in scored[:top_k]]

        if prune:
            return [self.pruner.prune(t) for t in top_tools]
        return top_tools

    def score_tool(self, intent_tokens: set[str], tool: dict[str, Any]) -> float:
        """Compute relevance score between query tokens and tool metadata."""
        name = tool.get("name", "").lower()
        desc = tool.get("description", "").lower()
        tool_tokens = set(name.replace("_", " ").replace("-", " ").split())
        tool_tokens.update(desc.replace("_", " ").replace("-", " ").split())

        schema = tool.get("inputSchema") or tool.get("parameters") or {}
        if isinstance(schema, dict):
            props = schema.get("properties", {})
            if isinstance(props, dict):
                for p in props.keys():
                    tool_tokens.update(p.lower().replace("_", " ").split())

        if not intent_tokens or not tool_tokens:
            return 0.0

        overlap = intent_tokens.intersection(tool_tokens)
        jaccard = len(overlap) / float(len(intent_tokens.union(tool_tokens)))

        # Name match bonus
        name_bonus = 0.5 if any(token in name for token in intent_tokens) else 0.0
        return round(jaccard + name_bonus, 4)
