# MCP Enablement Runbook

> Scope: **Connecting and Registering MCP Servers in Hath0r**  
> Rule: **cr-mcp-priority-001**

---

## 1. Registering an MCP Server

1. Open `cfg/mcp.servers.json`.
2. Append or edit server entry in the `servers` array.
3. Assign appropriate `scope` (`project`, `group`, or `org`).
4. Set `priority`: Ensure project MCP remains priority 1.
5. Set `enabled: true`.
6. Verify no inline tokens or credentials are added.

## 2. Validating the Configuration

7. Validate JSON syntax and schema compliance:
   ```bash
   hath0r doctor --mcp
   ```
8. Check live server endpoints:
   ```bash
   hath0r mcp check
   ```
9. Test tool invocation:
   ```bash
   hath0r mcp call <server-id> <tool-name> --args '{}'
   ```
