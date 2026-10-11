# Runbook: MLflow Service Operations & Diagnostics

> Artifact: **Runbook** · Suite: `hath0r-opensource` / `bayly-ai` / `1-nation`  
> Canonical Standard: `CR-CLI-FEATURE-STANDARD-001`, `CR-CICCCD-001`  
> Issue Reference: Bayly-AI/HATH0R-CLI#412  
> Date: 2026-10-11

## 1. Service Specifications (Hath0r OpenSource Default)

- **Container Name**: `HATH0R-MLflow` (service `mlflow` in `hath0r-opensource`)
- **Docker Group**: `hath0r` (`hath0r-opensource`)
- **Network**: `hath0r-net`
- **Internal Port**: `5000`
- **Edge URL**: `http://localhost:38000/mlflow/`
- **Direct Port Exposed to Host**: None (routed via `HATH0R-NGINX`)
- **Persistent Volume**: `hath0r_mlflow_data` mounted at `/data`

### Multi-Group Topology Matrix

| Group | Container | Compose File | Edge Proxy Port | Edge URL |
|---|---|---|---|---|
| `hath0r` (default) | `HATH0R-MLflow` | `cfg/docker/groups/hath0r/docker-compose.yml` | `38000` | `http://localhost:38000/mlflow/` |
| `1-nation` | `1NMLFLOW` | `deploy/docker/docker-compose.yml` | `58000` | `http://localhost:58000/mlflow/` |
| `bai` | `BAI-MLflow` | `cfg/docker/groups/bai/docker-compose.yml` | `48000` | `http://localhost:48000/mlflow/` |

---

## 2. Troubleshooting & Recovery

### Symptom: HTTP 502 Bad Gateway at `/mlflow/`
1. Check container health:
   ```bash
   docker inspect -f '{{.State.Status}} health={{if .State.Health}}{{.State.Health.Status}}{{else}}n/a{{end}}' HATH0R-MLflow
   ```
2. Check container logs:
   ```bash
   docker logs --tail 50 HATH0R-MLflow
   ```
3. Reload Edge reverse proxy if upstream DNS resolution lagged:
   ```bash
   docker exec HATH0R-NGINX nginx -s reload
   ```

### Symptom: Connection Reset / 403 Forbidden on API calls
Modern MLflow container images enforce host security middleware. Ensure the container command includes:
```bash
--allowed-hosts "*" --cors-allowed-origins "*" --static-prefix /mlflow
```
