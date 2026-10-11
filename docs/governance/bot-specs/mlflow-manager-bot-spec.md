# Bot Specification: MLflowManagerBot

> Artifact: **Bot Specification** · Member of **Artifact Hexad** (`CR-CLI-FEATURE-STANDARD-001`)  
> Identity: `mlflow_manager_bot`  
> Suite: `HATH0R-CLI` Control Tower  
> Issue Reference: Bayly-AI/HATH0R-CLI#412  
> Date: 2026-10-11

## 1. Role & Identity

`MLflowManagerBot` is an autonomous control-tower bot responsible for orchestrating, diagnosing, and reporting experiment tracking and continuous calibration telemetry across MLflow instances for all suite Docker meshes (`1-nation`, `hath0r`, `bai`).

---

## 2. Capabilities & Interface

### Core Methods
- `start_mlflow(group: str = "hath0r", detach: bool = True) -> Dict[str, Any]`
  - Launches container and verifies port availability.
- `stop_mlflow(group: str = "hath0r") -> Dict[str, Any]`
  - Stops container cleanly.
- `check_status(group: str = "hath0r", custom_endpoint: Optional[str] = None) -> Dict[str, Any]`
  - Probes edge and direct health endpoints (`http://localhost:38000/mlflow/`, etc.).
- `get_experiments(group: str = "hath0r", custom_endpoint: Optional[str] = None) -> List[Dict[str, Any]]`
  - Queries registered MLflow experiments via REST API.
- `get_runs(experiment_id: str, group: str = "hath0r", custom_endpoint: Optional[str] = None) -> List[Dict[str, Any]]`
  - Queries active and completed runs for the designated experiment.
- `log_run(experiment_name: str, run_name: str, params: Dict[str, Any], metrics: Dict[str, float], tags: Optional[Dict[str, str]] = None, group: str = "hath0r") -> Optional[str]`
  - Creates a new run, logs parameters and metrics, and marks status as `FINISHED`.

---

## 3. CLI Command Binding

Bound to `hath0r mlflow` CLI group:
```bash
hath0r mlflow status [--group <1-nation|hath0r|bai>] [--endpoint <url>] [--json]
hath0r mlflow up [--group <1-nation|hath0r|bai>] [--detach]
hath0r mlflow down [--group <1-nation|hath0r|bai>]
hath0r mlflow ui [--group <1-nation|hath0r|bai>] [--edge/--direct]
hath0r mlflow experiments [--group <1-nation|hath0r|bai>] [--json]
hath0r mlflow runs [--experiment-id <id>] [--group <1-nation|hath0r|bai>] [--json]
hath0r mlflow log [--experiment <name>] [--name <run_name>] [-p key=val] [-m key=val] [--group <1-nation|hath0r|bai>]
```
