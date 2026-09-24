# JEV — Next Steps for the Team

**Audience:** Operators, MCP owners, CODEOWNERS (`@somesayray`)  
**As of:** 2026-09-24  
**Prerequisite:** Integration shipped on `development` (see [jev-integration.md](jev-integration.md))

---

## Where we are

| Done | Not done yet |
|------|----------------|
| Tool-guard code on BAI / Hath0r / 1-Nation MCP | Guard **enabled** in running containers (`JEV_MODE` still off) |
| CLI inventory + framework `lib/jev/` | Human **approval channel** for `confirm`/`review` |
| Unit/integration tests (20 per MCP) | Search **rerank / answerability** JEV path |
| Docs + rollout PRs merged | Staging/prod **live** key + fail-closed policy |
| | Repo **SONAR_TOKEN** where QG is required |

---

## Priority backlog

### P0 — Make guard operable in environments (this sprint)

1. **Secrets**  
   - Store TypeSafe/JEV key under `Development/.credentials/` (never git).  
   - Wire into Compose/K8s for BAI-MCP, hath0r-mcp, 1NMCP as `JEV_API_KEY` or `TYPESAFE_API_KEY`.

2. **Enable by environment**  
   | Env | Suggested `JEV_MODE` | `JEV_ON_ERROR` |
   |-----|----------------------|----------------|
   | local | `stub` or `off` | `allow` |
   | development | `stub` or `live` | `allow` |
   | staging | `live` | `deny` for irreversible tools |
   | production | `live` (after approval UX) | `deny` for delete/remove |

3. **Recreate containers** after env change; re-run smoke: mutating `tools/call` should return `jev_tool_guard_blocked` under stub/live.

4. **SONAR_TOKEN** on HATH0R-CLI / Framework / 1-Nation (and others) so Quality Gate is a real gate, not an infra false fail.

### P1 — Production policy (next sprint)

1. **Decision matrix** — stop treating all non-`allow` as permanent blocks:  
   - `deny` → always block  
   - `confirm`/`review` → block **unless** operator approval (header/arg/allow-list TTL)  
   - Never let approval override `deny`

2. **Catalog CI check** — fail build if a new mutating MCP tool is registered but missing from `GUARDED_TOOL_PROFILES` / `cfg/jev.json`.

3. **Audit** — persist decision, confidence, source, blocked flag on MCP activity / `kb_status_full`.

4. **Runbook** — enable/disable, key rotation, break-glass bypass, incident rollback (document under `docs/governance/playbooks/` or ops runbook).

### P2 — Product leverage (following)

1. **Hybrid search** — optional JEV Score/Noul on hits (`use_reranker` already true in RAG cfg); keep off pure high-QPS health paths.  
2. **Completion preset** — after `kb_sync_all` / bulk ingest, “is the objective done?”  
3. **Optional MCP tools** — `jev_decide` / research for agents that want explicit calls.  
4. **Shared package** — publish/consume framework `lib/jev` instead of copied modules (reduce drift).

### P3 — Suite hygiene

1. Clarify Hath0r/1-Nation **entrypoints**: FastMCP read-only vs full API with mutations.  
2. Rebuild images from current `development` so all nodes run the same guard binary.  
3. Track productionization as a single epic/issue with AC from [jev-integration.md](jev-integration.md) § purpose.

---

## Owner checklist (copy for standup)

- [ ] Credentials file present; Compose/K8s env documented  
- [ ] Dev stack recreated with `JEV_MODE=stub`; smoke shows block on delete  
- [ ] Staging plan for `live` + fail-closed on irreversible tools  
- [ ] Approval path design agreed (who signs `confirm`?)  
- [ ] Sonar secrets on all repos that require QG  
- [ ] One tracking issue/epic for “JEV production-ready” with P0–P2 AC  

---

## Quick commands

```bash
hath0r jev status

# Tests
cd ~/Development/BAI/MCP && PYTHONPATH=src pytest tests/unit/test_jev_tool_guard.py tests/integration -q --no-cov

# Health
curl -sS http://127.0.0.1:48080/health
curl -sS http://127.0.0.1:38083/health
curl -sS http://127.0.0.1:58083/health
```

---

## References

- Wiki: [jev-integration.md](jev-integration.md)  
- POC: [../jev-tool-guard-poc.md](../jev-tool-guard-poc.md)  
- Perf: [../jev-tool-guard-performance.md](../jev-tool-guard-performance.md)  
- Config: [`cfg/jev.json`](../../cfg/jev.json)  
