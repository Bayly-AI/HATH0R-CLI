# BAI Docker group

> Template mirrors 1-Nation ATC group pattern for BAI ATC+MCP+UXP+Redis+NGINX.  
> Prefer ATC-owned compose under `BAI/ATC/deploy/docker/` when present; this file is the control-tower contract.

## Expected services

| Service | Default host port env | Role |
|---------|----------------------|------|
| redis | — | shared state (`BAI-Redis`) |
| nginx | `BAI_NGINX_HOST_PORT` (48000) | shared edge |
| atc | `BAI_ATC_HOST_PORT` | config manager |
| mcp | `BAI_MCP_HOST_PORT` (48080) | knowledge MCP |
| uxp | `BAI_UXP_HOST_PORT` | experience |

## Clone pattern

Copy `cfg/docker/groups/hath0r/docker-compose.yml`, rename containers/network to `bai-*` / `BAI-*`, and point images at BAI build artifacts. Keep ATC as config manager.

Secrets: `Development/.credentials/bai/.env` — never commit.
