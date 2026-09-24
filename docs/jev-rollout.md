# JEV rollout across Development repositories

**Date:** 2026-09-24  
**Decision model:** TypeSafe JEV (System One) — typed allow/confirm/review/deny for agent tool calls.

## Status by repository

| Repository | JEV integration | Notes |
|------------|-----------------|-------|
| **BAI/MCP** | **Full** | Tool-guard on mutating MCP tools; tests + docs |
| **OpenSource/hath0r-mcp** | **Full** | Tool-guard hook + FastMCP suite_info/kb_search JEV metadata |
| **1-Nation/MCP** | **Full** | Same as hath0r-mcp |
| **OpenSource/hathor-cli** | **Status CLI** | `hath0r jev status` reports env + integration paths |
| **OpenSource/hath0r-framework** | **Reference lib** | `lib/jev/` portable copies |
| **OpenSource/hath0r-atc** | N/A (infra) | Consumes MCP decisions; no tool executor |
| **1-Nation/ATC** | N/A (infra) | Same |
| **OpenSource/hath0r-poc** | Archived | No active control loop |
| **BAI/UXP**, **1-Nation/UXP**, **Websites/** | N/A (UI) | Call MCPs that enforce JEV; do not embed API keys in browsers |

## Enable everywhere (operator)

```bash
# Recommended local/dev
export JEV_MODE=stub

# Staging/prod (server-side only)
export JEV_MODE=live
export JEV_API_KEY=...   # from Development/.credentials — never commit
```

Per-service: see `cfg/jev.json` and `docs/jev-tool-guard-poc.md` in each MCP.

## Verify

```bash
# CLI inventory
cd OpenSource/hathor-cli && python -m hath0r_cli jev status   # or: hath0r jev status

# MCP unit tests (BAI reference)
cd BAI/MCP && PYTHONPATH=src pytest tests/unit/test_jev_tool_guard.py -q --no-cov
cd OpenSource/hath0r-mcp && PYTHONPATH=src pytest tests/unit/test_jev_tool_guard.py -q --no-cov
cd 1-Nation/MCP && PYTHONPATH=src pytest tests/unit/test_jev_tool_guard.py -q --no-cov
```
