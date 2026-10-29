# Runbook: Task Evaluation Service & Telemetry Operations

> Canonical Operations Runbook · ID: `RB-TASK-EVAL-001`  
> Epic: #510 · Suite: `hath0r-opensource`

---

## 1. Architecture & Endpoints

| Component | Container | Local Endpoint | Role in Task Evals |
|---|---|---|---|
| **TaskEvaluatorBot** | Local CLI (`hath0r`) | `.hath0r/evals/latest.json` | Executes 4-tier evaluation and enforces pre-completion gate |
| **Arize Phoenix** | `Hath0r-phoenix` | `http://localhost:36006/phoenix/` | Receives OTel `EVALUATOR` spans (`hath0r.eval.task`) |
| **MLflow Tracking** | `Hathor-MLFLOW` | `http://localhost:35000/mlflow/` | Logs `hath0r-task-evals` experiment runs, params, and reward metrics |

---

## 2. Operational Checks

### Verify Local Scorecard & Hash Integrity
```bash
hath0r evals verify
hath0r memory hash verify
```

### Verify Phoenix & MLflow Connectivity
```bash
hath0r phoenix status --group hath0r
hath0r phoenix evals --suite hath0r
hath0r mlflow status --group hath0r
```

---

## 3. Offline Telemetry Spooling & Recovery

When `Hath0r-phoenix` or `Hathor-MLFLOW` containers are offline during local development:
1. `TaskEvaluatorBot` records `"observability_sync": {"mode": "spooled_local"}` in `.hath0r/evals/latest.json` and `.hath0r/evals/history/eval-<task_id>.json`.
2. The local evaluation gate still succeeds if $R_{\text{task}} \ge 0.80$ and all hard gates pass.
3. Once `make -C /Users/raybayly/Development/OpenSource/hath0r-atc docker-up` brings Phoenix and MLflow online, running `hath0r evals run --sync-observability` pushes the metrics to the active collectors.
