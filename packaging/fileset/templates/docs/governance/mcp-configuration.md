# Model Context Protocol (MCP) Configuration Specification

> Product: **HATH0R Agentic Framework & Ecosystem**  
> Rule: **cr-mcp-priority-001**  
> Status: **Canonical Specification**  
> Updated: 2026-09-24

---

## 1. Overview & Core Rules

Hath0r orchestrates multiple Model Context Protocol (MCP) servers providing tool calls, knowledgebase lookups, and specialized actions. All MCP connections are declaratively managed through a repository-local configuration file (`cfg/mcp.servers.json`).

### Priority Ordering Rule (CRITICAL)
- **Project MCP is ALWAYS Priority #1**:
  - The local repository's project-specific MCP server (e.g., `hath0r-mcp`) must always precede group and org servers.
  - Priority resolution strictly follows:
    1. Scope `project` (Priority 1)
    2. Scope `group`
    3. Scope `org` / `user`
    4. Numeric `priority` ascending within matching scope.
- **Config-Driven Dynamism**: Adding, removing, or disabling MCP servers requires no code changes—only updating `cfg/mcp.servers.json`.
- **Zero Secrets**: Secrets, API keys, and credentials must NEVER be placed in `cfg/mcp.servers.json`. Use `env_ref` pointing to `/Users/raybayly/Development/.credentials/<service>/.env`.

---

## 2. Configuration Schema (`cfg/mcp.servers.json`)

```json
{
  "version": "1.0",
  "description": "Configured MCP servers for this repository",
  "servers": [
    {
      "id": "hath0r-mcp",
      "name": "Hath0rMCP",
      "scope": "project",
      "group": "hath0r-opensource",
      "priority": 1,
      "enabled": true,
      "transport": "streamable-http",
      "base_url": "http://127.0.0.1:38083",
      "mcp_endpoint": "/mcp",
      "health_endpoint": "/health",
      "ready_endpoint": "/ready"
    }
  ]
}
```

---

## 3. Validation & Doctor Checks

1. **Schema Compliance**: Validated against `contracts/hath0r-mcp-servers-v1.schema.json`.
2. **Project MCP Presence**: `hath0r doctor` or runner verifies that at least one `project`-scoped server is configured and enabled.
3. **Connectivity Probing**: `hath0r mcp check` verifies HTTP endpoints and tool discovery across all enabled servers.
