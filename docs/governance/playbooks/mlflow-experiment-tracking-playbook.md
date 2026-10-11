# Playbook: MLflow Experiment Tracking & Calibration Auditing

> Artifact: **Playbook** · Suite: `hath0r-opensource` / `bayly-ai` / `1-nation`  
> Canonical Standard: `CR-CLI-FEATURE-STANDARD-001`, `CR-CICCCD-001`  
> Issue Reference: Bayly-AI/HATH0R-CLI#412  
> Date: 2026-10-11

## 1. Scenario: CCCD Calibration Drift Detection & Sweep Audit

When CCCD telemetry reports prompt degradation or parameter drift:
1. **Verify Tracking Status**:
   ```bash
   hath0r mlflow status --group 1-nation
   ```
2. **Execute On-Demand Calibration**:
   ```bash
   hath0r cccd calibrate --iterations 5 --signature statutory_summarizer_signature
   ```
3. **Audit Generated Runs in MLflow**:
   ```bash
   hath0r mlflow runs -e 1 --group 1-nation
   ```
4. **Compare Optimal Hyperparameters**:
   Inspect the latest run to verify S/N ratio improvement and Taguchi loss reduction relative to baseline runs.

---

## 2. Scenario: Storage Maintenance & Database Vacuuming

Over time, SQLite database `/data/mlflow.db` and `/data/artifacts/` accumulate run histories.
1. Inspect volume usage:
   ```bash
   docker exec 1NMLFLOW du -sh /data/mlflow.db /data/artifacts
   ```
2. Vacuum database:
   ```bash
   docker exec 1NMLFLOW python -c "import sqlite3; con=sqlite3.connect('/data/mlflow.db'); con.execute('VACUUM'); con.close()"
   ```
