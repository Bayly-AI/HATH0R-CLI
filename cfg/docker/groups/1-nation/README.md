# 1-Nation Docker group

> Canonical compose lives in ATC (config manager):  
> `/Users/raybayly/Development/1-Nation/ATC/deploy/docker/docker-compose.yml`  
> Control-tower issue: HATH0R-CLI #63 · member issues mirror.

## Topology

| Role | Container | Notes |
|------|-----------|-------|
| Shared state | `1NRedis` | redis:7-alpine |
| Shared edge | `1NGINX` | host port default 58000 |
| ATC | (ATC stack) | config manager for group |
| MCP | `1NMCP` | see 1-Nation/MCP/docker-compose.yml |
| UXP | experience service | profile `apps` |

## Operator

```bash
# From 1-Nation ATC checkout
docker compose -f deploy/docker/docker-compose.yml up -d redis nginx
docker compose -f deploy/docker/docker-compose.yml --profile apps up -d
```

Secrets: `Development/.credentials/` only — never commit.
