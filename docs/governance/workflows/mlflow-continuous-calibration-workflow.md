# Workflow: MLflow Continuous Calibration & MLOps Pipeline

> Artifact: **Workflow** · Suite: `hath0r-opensource` / `bayly-ai` / `1-nation`  
> Canonical Standard: `CR-CLI-FEATURE-STANDARD-001`, `CR-CICCCD-001`  
> Issue Reference: Bayly-AI/HATH0R-CLI#412  
> Date: 2026-10-11

## 1. Overview

This workflow links Continuous Calibration (CC) triggers to MLflow experiment tracking.

```mermaid
sequenceDiagram
    autonumber
    participant Agent as Operator / CCCD Bot
    participant CCCD as Calibration Loop
    participant Taguchi as Taguchi Optimizer
    participant MLflow as MLflow Manager Bot
    participant 1NMLFLOW as 1NMLFLOW Container

    Agent->>CCCD: run_calibration(signature, iterations)
    CCCD->>Taguchi: optimize_parameters(factors, levels)
    Taguchi-->>CCCD: optimal_parameters, mean_snr_db, quality_loss
    CCCD->>MLflow: log_run(experiment="cccd-calibration", params, metrics)
    MLflow->>1NMLFLOW: POST /ajax-api/2.0/mlflow/runs/create
    MLflow->>1NMLFLOW: POST /ajax-api/2.0/mlflow/runs/log-parameter
    MLflow->>1NMLFLOW: POST /ajax-api/2.0/mlflow/runs/log-metric
    MLflow->>1NMLFLOW: POST /ajax-api/2.0/mlflow/runs/update (FINISHED)
    MLflow-->>CCCD: return run_id
    CCCD-->>Agent: calibration complete (with mlflow_run_id)
```

---

## 2. Automated Pipeline Steps

1. **Trigger**: Calibration initiated via `hath0r cccd calibrate`, periodic auto-tune daemon, or PR promotion gate.
2. **Execution**: DSPy compile and Taguchi OATS array evaluation.
3. **Tracking**: Optimal hyperparameters and loss metrics written to MLflow database.
4. **Validation**: Quality gate validates S/N ratio against threshold before parameter promotion.
