# MLflow Management Procedure

> Artifact: **Procedure** · Suite: `hath0r-opensource` / `bayly-ai` / `1-nation`  
> Canonical Standard: `CR-CLI-FEATURE-STANDARD-001`, `CR-CICCCD-001`  
> Issue Reference: Bayly-AI/HATH0R-CLI#412  
> Date: 2026-10-11

## 1. Purpose

Defines the standard procedure for managing MLflow tracking server lifecycle, monitoring server health, querying experiments, and executing calibration logging.

---

## 2. Server Lifecycle Management

### Starting the Tracking Server
1. Check existing server state:
   ```bash
   hath0r mlflow status --group 1-nation
   ```
2. If inactive, launch the container:
   ```bash
   hath0r mlflow up --group 1-nation
   ```
3. Verify readiness via Edge:
   ```bash
   curl -I http://localhost:58000/mlflow/
   ```

### Stopping the Tracking Server
1. Verify no active calibration runs are in progress.
2. Stop the container cleanly:
   ```bash
   hath0r mlflow down --group 1-nation
   ```

---

## 3. Experiment and Run Inspection

1. List all active experiments:
   ```bash
   hath0r mlflow experiments --group 1-nation
   ```
2. List runs within an experiment ID:
   ```bash
   hath0r mlflow runs -e 1 --group 1-nation
   ```
3. Open the web interface:
   ```bash
   hath0r mlflow ui --group 1-nation
   ```

---

## 4. Manual Calibration Logging

For ad-hoc benchmarking or offline parameter evaluation:
```bash
hath0r mlflow log -e cccd-calibration -n manual_benchmark \
  -p temperature=0.2 -p top_p=0.95 \
  -m mean_snr_db=28.4 -m quality_loss=0.005 \
  --group 1-nation
```
