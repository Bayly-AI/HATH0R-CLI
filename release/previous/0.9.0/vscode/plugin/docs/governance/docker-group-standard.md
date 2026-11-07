# Docker group standard (ATC + MCP + UXP + Redis + NGINX)

> Control tower: `Bayly-AI/HATH0R-CLI` · Issue #63

## Topology

Per product family (`hath0r`, `1-nation`, `bai`):

1. **Redis** — shared state  
2. **NGINX** — shared edge  
3. **ATC** — **config manager** for the group  
4. **MCP** — knowledge/tools  
5. **UXP** — experience UI  

## Templates

| Group | Path |
|-------|------|
| Hath0r | `cfg/docker/groups/hath0r/docker-compose.yml` |
| 1-Nation | ATC canonical + `cfg/docker/groups/1-nation/README.md` |
| BAI | `cfg/docker/groups/bai/docker-compose.yml` |

## Workflows

- `cfg/docker/workflows/hath0r-docker-group.json`
- `cfg/docker/workflows/hath0r-opensource-core.json`

Validate: `hath0r docker workflow validate <file>`

## Docs set

Strategy/procedure/playbook/runbook/checklist under `docs/governance/*` with `docker-group` id.
