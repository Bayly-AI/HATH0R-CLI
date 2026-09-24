# Playbook — Docker group bring-up

1. Ensure images exist or use redis/nginx-only first.
2. `docker compose -f cfg/docker/groups/<group>/docker-compose.yml up -d redis nginx`.
3. Validate workflow: `hath0r docker workflow validate cfg/docker/workflows/hath0r-docker-group.json`.
4. `--profile apps` when ATC/MCP/UXP images ready.
5. ATC remains config manager; do not fork ports without env overrides.
