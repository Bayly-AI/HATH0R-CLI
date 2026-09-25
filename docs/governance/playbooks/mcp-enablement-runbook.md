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

## 3. Operating 1-Nation vote sources

The `1-nation-mcp` source catalog is the only authority for its outbound federal
vote-source routes. Do not bypass it with curl, source-specific scripts, or
credential-bearing CLI flags.

```bash
hath0r --output json mcp sources list
hath0r --output json mcp sources test house-clerk-rollcall
hath0r --output json mcp sources fetch-sample house-clerk-rollcall
hath0r --output json mcp sources test senate-lis-rollcall
hath0r --output json mcp sources fetch-sample senate-lis-rollcall
```

`congress-gov-v3` returns `credential_required` until 1N-MCP receives its key
from `/Users/raybayly/Development/.credentials/congress-gov/.env`. That result
is a safe configuration state and must never reveal a credential value.
