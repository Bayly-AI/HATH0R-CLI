# OpenFeature standards — setup and adherence

> Control tower: `Bayly-AI/HATH0R-CLI` · Issue track: #59  
> Applies org-wide across product groups.

## Policy (CRITICAL)

1. **OpenFeature is the canonical feature-flag API** for runtime toggles (no ad-hoc `if ENV_FLAG` sprawl for product behavior).
2. Flag evaluation MUST go through an OpenFeature-compatible client/provider abstraction.
3. Flag keys are **stable, lowercase, dotted or kebab** identifiers (e.g. `jev.tool_guard.mode`, `mcp.kb.hybrid_search`).
4. Default values ship safe-for-production (fail closed for mutating/dangerous paths).
5. Providers and remote config URLs are configured via env/config — **no secrets in repo**.
6. Evaluation context SHOULD include: `targetingKey` / principal (non-PII when possible), `environment`, `product`, `service.name`.

## Configuration surface

- `cfg/feature-flags/openfeature.json` — provider kind, defaults, flag catalog pointers
- Env:
  - `OPENFEATURE_PROVIDER` (`in-memory` | `env` | `file` | vendor)
  - `OPENFEATURE_PROVIDER_OPTIONS` (JSON string; secrets via env interpolation outside git)

## Flag catalog expectations

Each product maintains a short catalog (markdown or JSON) listing:

| Flag key | Type | Default | Owner | Notes |
|----------|------|---------|-------|-------|
| example.flag | boolean | false | team | … |

Control tower example catalog: `cfg/feature-flags/catalog.example.json`.

## Correlation with observability

When OTel is enabled, attach flag keys/values used for a request as span attributes under `feature_flag.*` (OpenFeature semantic conventions where available). Never attach secrets.

## Adherence checklist

`docs/governance/checklists/openfeature-adherence.md`

## Playbook / runbook

- `docs/governance/playbooks/openfeature-setup-playbook.md`
- `docs/governance/runbooks/openfeature-ops-runbook.md`
