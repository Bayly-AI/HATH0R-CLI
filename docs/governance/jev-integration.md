# JEV Integration Wiki — AegisCMCP & Suite

**Status:** Shipped on `development` (2026-09-24)  
**Decision model:** TypeSafe **JEV** (System One) — typed decisions, not prose generation  
**Owner surface:** MCP agent control loop (`tools/call` → mutating tools)

---

## 1. Purpose

JEV sits **in front of consequential MCP tool execution**. Agents still plan and call tools; JEV returns a structured verdict the server enforces:

| Decision | Meaning |
|----------|---------|
| `allow` | Proceed with the tool |
| `confirm` | Needs explicit human confirmation (POC: blocked) |
| `review` | Ambiguous / escalate (POC: blocked) |
| `deny` | Do not execute |

JEV does **not** replace Q-Gates, branch rules, Docker policy, or bearer auth. Probabilities are **signals**; application policy still owns authorization.

---

## 2. Architecture

```text
Agent (Warp / Claude / …)
        │  MCP tools/call
        ▼
┌───────────────────────────────────────┐
│  MCP server (BAI / Hath0r / 1-Nation) │
│  _execute_mcp_tool(name, args)        │
│         │                             │
│         ├─ read-only tool ──► handler │
│         │                             │
│         └─ mutating + JEV on?         │
│                 │                     │
│                 ▼                     │
│         jev_tool_guard / jev_client   │
│         allow | confirm | review | deny│
│                 │                     │
│        block (isError JSON) | run     │
└───────────────────────────────────────┘
```

### Key modules (MCP)

| Path | Role |
|------|------|
| `src/knowledgebase/core/jev_client.py` | Env settings, stub/live HTTP, response parse |
| `src/knowledgebase/core/jev_tool_guard.py` | Risk catalog for mutating tools + evaluate/format |
| `src/knowledgebase/api/main.py` | Hook inside `_execute_mcp_tool` |
| `cfg/jev.json` | Operator reference (modes, guarded tool list, env) |
| `docs/jev-tool-guard-poc.md` | Enablement & try-it |
| `docs/jev-tool-guard-performance.md` | Measured overhead |

### Guarded tools (representative)

Mutations only — e.g. `kb_index_delete`, `kb_remove_document`, `kb_sync_all`, `kb_add_document`, `kb_index_directory`, `runbook_create` / `delete`, config setters.  
**Not guarded:** `kb_search`, `kb_get_document`, health/stats, docs read tools.

---

## 3. Suite rollout map

| Repository | Integration | Merge |
|------------|-------------|-------|
| **BAI/MCP** (AegisCMCP) | Full tool-guard + tests | On `development` (pre-rollout + baseline) |
| **HATH0R-MCP** | Full tool-guard + FastMCP metadata | PR [#7](https://github.com/Bayly-AI/HATH0R-MCP/pull/7) |
| **1-Nation-MCP** | Full tool-guard + FastMCP metadata | PR [#25](https://github.com/Bayly-AI/1-Nation-MCP/pull/25) |
| **HATH0R-CLI** | `hath0r jev status` + rollout doc | PR [#102](https://github.com/Bayly-AI/HATH0R-CLI/pull/102) / tip |
| **HATH0R-Agentic-Framework** | Portable `lib/jev/` reference | PR [#60](https://github.com/Bayly-AI/HATH0R-Agentic-Framework/pull/60) |
| ATC / UXP / Websites | N/A | No local tool executor; call MCPs only |

Inventory CLI:

```bash
hath0r jev status
# or: cd OpenSource/hathor-cli && PYTHONPATH=src python -m hath0r_cli.cli jev status
```

---

## 4. Configuration

### Environment variables

| Variable | Values | Notes |
|----------|--------|-------|
| `JEV_MODE` | `off` (default), `stub`, `live` | Primary switch |
| `JEV_API_KEY` / `TYPESAFE_API_KEY` | Bearer token | Live only; never commit |
| `JEV_ENDPOINT` | URL | Default tool-guard preset URL |
| `JEV_PROTOCOL` | `preset` \| `systemone` | Request shape |
| `JEV_TIMEOUT_SECONDS` | e.g. `2.5` | Hard ceiling recommended ≤5s |
| `JEV_ON_ERROR` | `allow` \| `deny` | Behavior if live JEV fails |
| `JEV_MIN_CONFIDENCE` | `0.0`–`1.0` | Optional allow floor |

### Modes

| Mode | Behavior |
|------|----------|
| **off** | No JEV calls; zero overhead on hot path |
| **stub** | Deterministic local heuristics (no API key); good for demos/CI |
| **live** | HTTP call to JEV; requires API key |

Secrets: `/Users/raybayly/Development/.credentials/<service>/.env` → inject into Compose/K8s. **Never** put keys in UXP/browser bundles.

### Enable in Docker

Recreate MCP containers with env set, e.g.:

```bash
# docker-compose or -e
JEV_MODE=stub
# or live + JEV_API_KEY=...
```

Then restart so the process picks up env (images already contain code on `development`).

---

## 5. Verification (smoke)

```bash
# Unit + integration (each MCP)
cd BAI/MCP && PYTHONPATH=src pytest tests/unit/test_jev_tool_guard.py tests/integration/test_jev_tool_guard_integration.py -q --no-cov
# Expect: 20 passed (same pattern on hath0r-mcp / 1-Nation MCP)

# Health (local ports)
curl -sS http://127.0.0.1:48080/health   # BAI-MCP
curl -sS http://127.0.0.1:38083/health   # hath0r-mcp
curl -sS http://127.0.0.1:58083/health   # 1NMCP

# With JEV_MODE=stub in process: mutating tools return jev_tool_guard_blocked
```

**Perf (local, prior measurement):** off ≈ 0 ms · stub ≈ +1–2 ms e2e · live ≈ JEV RTT (tens–hundreds of ms). Details: [jev-tool-guard-performance.md](../jev-tool-guard-performance.md).

---

## 6. Operations notes

- **Default off in production containers** until explicitly enabled — safe roll-forward.  
- **POC policy:** `confirm` and `review` are treated as **blocks** (agents cannot self-approve).  
- **SonarCloud:** several repos still need `SONAR_TOKEN` for a real QG; QG failures during rollout were often missing secrets, not JEV code defects.  
- **Read-only FastMCP** entrypoints (Hath0r/1-Nation small server) expose suite tools only; full mutating catalog is on the legacy/full API path (BAI full list on `:48080`).

---

## 7. Related docs

| Doc | Location |
|-----|----------|
| POC enablement | [jev-tool-guard-poc.md](../jev-tool-guard-poc.md) |
| Performance | [jev-tool-guard-performance.md](../jev-tool-guard-performance.md) |
| Suite rollout map | CLI `docs/jev-rollout.md` · Framework `docs/jev-rollout.md` |
| Next steps (team) | [jev-next-steps.md](jev-next-steps.md) |
| Config | [`cfg/jev.json`](../../cfg/jev.json) |

---

## 8. Change history

| Date | Event |
|------|--------|
| 2026-09-23 | BAI/MCP JEV tool-guard POC + tests |
| 2026-09-24 | Suite rollout PRs merged: HATH0R-MCP #7, 1-Nation-MCP #25, Framework #60, HATH0R-CLI #102 |
| 2026-09-24 | Smoke: 60 automated tests green; containers healthy; guard idle until `JEV_MODE` set |
