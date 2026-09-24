# Runbook — Docker group

## Redis unhealthy
- `docker logs HATH0R-Redis`; ensure volume writable.

## Port conflict
- Override `HATH0R_*_HOST_PORT` env vars.

## Apps profile image missing
- Build local images or run redis/nginx only.
