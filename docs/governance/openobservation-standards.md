# OpenObservation standards — setup and adherence

> Control tower: `Bayly-AI/HATH0R-CLI` · Issue track: #58  
> Org-wide observability *intent* and SLI baseline (pairs with OpenTelemetry implementation).

## Intent

**OpenObservation** defines *what* we observe and the operator-facing baseline: SLIs/SLOs, golden signals, audit/event classes, and dashboard/alert expectations.  
**OpenTelemetry** defines *how* signals are produced and exported (`opentelemetry-standards.md`).

## Golden signals (required per service)

1. **Latency** — p50/p95 for primary request or tool-call path  
2. **Traffic** — requests / tool invocations per minute  
3. **Errors** — error rate by class (4xx/5xx or app codes)  
4. **Saturation** — queue depth, pool wait, CPU/memory where applicable  

## Event / audit classes

| Class | Examples | Retention guidance |
|-------|----------|--------------------|
| `security` | authz deny, secret access attempt | longest; restricted |
| `governance` | branch guard block, quality gate fail | medium |
| `ops` | deploy, factory run, container health | medium |
| `product` | domain business events | per product policy |

Telemetry spool (Hath0r): `.hath0r/spool/telemetry-*.jsonl` — never blocks primary UX; never contains secrets.

## SLI defaults (suite)

| SLI | Target (dev/test) | Notes |
|-----|-------------------|-------|
| MCP `/health` success | ≥ 99% rolling 24h local | |
| Tool call error rate | < 5% excluding client 4xx | |
| Factory step abort rate | tracked per factory_id | |
| PR quality gate flake | investigate > 2 consecutive infra fails | Sonar token missing = infra |

## Configuration surface

- `cfg/observability/openobservation.json` — SLI names, alert hooks (urls via env), dashboard links
- Dashboards/alerts are **referenced**, not hardcoded with credentials

## Adherence checklist

`docs/governance/checklists/openobservation-adherence.md`

## Playbook / runbook

- `docs/governance/playbooks/openobservation-setup-playbook.md`
- `docs/governance/runbooks/openobservation-ops-runbook.md`
