# MCP Server Enablement Checklist

## Configuration Checklist
- [ ] Server declared in `cfg/mcp.servers.json`.
- [ ] Conforms to `contracts/hath0r-mcp-servers-v1.schema.json`.
- [ ] **Project MCP is priority 1**; group/org servers follow in sequence.
- [ ] No hardcoded secrets or sensitive tokens.
- [ ] Endpoints (`base_url`, `mcp_endpoint`, `health_endpoint`) configured correctly.

## Operational Verification Checklist
- [ ] `hath0r mcp list` displays server with correct priority.
- [ ] `hath0r mcp check` passes health checks and discovers available tools.
- [ ] Test tool execution via `hath0r mcp call` succeeds.
