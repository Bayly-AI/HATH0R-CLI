# Suite standards index (control tower)

> **Canonical owner:** `Bayly-AI/HATH0R-CLI`  
> Member repos link here via their `docs/governance/SUITE_STANDARDS.md` pointers.  
> Updated: 2026-09-24 · Closure: see `project-closure-suite-epics-2026-09-24.md`

## Standards

| Standard | Doc | Config stubs | Issue track |
|----------|-----|--------------|-------------|
| OpenTelemetry | [opentelemetry-standards.md](./opentelemetry-standards.md) | `cfg/observability/otel.json` | #60 |
| OpenFeature | [openfeature-standards.md](./openfeature-standards.md) | `cfg/feature-flags/openfeature.json` | #59 |
| OpenObservation | [openobservation-standards.md](./openobservation-standards.md) | `cfg/observability/openobservation.json` | #58 |
| CLI-first | [cli-first-rules.md](./cli-first-rules.md) + root `AGENTS.md` | session checklist | #61 |
| Workflow documentation | [workflow-documentation-standard.md](./workflow-documentation-standard.md) | factory inventory in doc | #62 |
| Docker groups | [docker-group-standard.md](./docker-group-standard.md) | `cfg/docker/groups/*` | #63 |
| SemVer | [semantic-versioning.md](./semantic-versioning.md) | root `VERSION` | historical |
| Quality / release bots | [quality-bots.md](./quality-bots.md) | `cfg/quality-gates.json` | #66–#71 |
| MCP servers (priority) | [mcp-configuration.md](./mcp-configuration.md) | `cfg/mcp.servers.json` | suite |

## Docker group templates

| Group | Path |
|-------|------|
| Hath0r | `cfg/docker/groups/hath0r/docker-compose.yml` |
| BAI | `cfg/docker/groups/bai/docker-compose.yml` |
| 1-Nation | ATC canonical + `cfg/docker/groups/1-nation/README.md` |

Workflows: `cfg/docker/workflows/hath0r-docker-group.json`, `hath0r-opensource-core.json`

## Member inheritance

Fan-out targets keep a local `SUITE_STANDARDS.md` that points at this index (and/or raw GitHub `development` paths) and may copy cfg stubs with product-specific `service.name`.
