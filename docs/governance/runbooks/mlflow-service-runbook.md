# Runbook: MLflow Service Operations & Diagnostics

> Artifact: **Runbook** · Suite: `hath0r-opensource` / `bayly-ai` / `1-nation`  
> Canonical Standard: `CR-DOCKER-1N-GROUP-001`, `CR-DOCKER-1N-EDGE-001`, `CR-CLI-FEATURE-STANDARD-001`  
> Issue Reference: Bayly-AI/HATH0R-CLI#412  
> Date: 2026-10-11

## 1. Service Specifications

- **Container Name**: `1NMLFLOW`
- **Docker Group**: `1-nation`
- **Network**: `1-nation-net`
- **Internal Port**: `5000`
- **Edge URL**: `http://localhost:58000/mlflow/`
- **Direct Port Exposed to Host**: None (`CR-DOCKER-1N-EDGE-001`)
- **Persistent Volume**: `1n_mlflow_data` mounted at `/data`

---

## 2. Troubleshooting & Recovery

### Symptom: HTTP 502 Bad Gateway at `/mlflow/`
1. Check container health:
   ```bash
   docker inspect -f '{{.State.Status}} health={{if .State.Health}}{{.State.Health.Status}}{{else}}n/a{{end}}' 1NMLFLOW
   ```
2. Check container logs:
   ```bash
   docker logs --tail 50 1NMLFLOW
   ```
3. Reload Edge reverse proxy if upstream DNS resolution lagged:
   ```bash
   docker exec 1NEDGE nginx -s reload
   ```

### Symptom: Connection Reset / 403 Forbidden on API calls
Modern MLflow container images enforce host security middleware. Ensure the container command includes:
```bash
--allowed-hosts "*" --cors-allowed-origins "*" --static-prefix /mlflow
```
