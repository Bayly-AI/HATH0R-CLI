# Dynamic MCP Server Mounting & Security Policy Playbook

> Scope: **Developer & Operator Runbook for MCP Dynamic Mounting & In-Flight Guardrails**  
> Rule Reference: **CR-CLI-ENTRY-001 / CR-SUBSTRATE-001**  
> Issue: **#243**

---

## 1. Quick Start

### Dynamically Connecting an MCP Server
```bash
hath0r mcp connect sqlite-server --command "npx -y @modelcontextprotocol/server-sqlite --db /tmp/test.db"
```

### Performing In-Flight Security Inspection on a Tool Call
```bash
hath0r mcp inspect --server sqlite-server --tool query --args '{"sql": "SELECT * FROM users"}'
```

### Testing Security Policy Against Unsafe Injections
```bash
hath0r mcp inspect --server shell-server --tool exec --args '{"cmd": "rm -rf /"}'
```
*(Returns `BLOCKED: Dangerous system command pattern detected`)*

---

## 2. Listing Active Dynamic MCP Policies
```bash
hath0r mcp policy list
```
