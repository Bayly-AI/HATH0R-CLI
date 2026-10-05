# Bot Specification: PhoenixManagerBot

> Artifact: **Bot Specification** · Member of **Artifact Hexad** (`CR-CLI-FEATURE-STANDARD-001`)  
> Identity: `phoenix_manager_bot`  
> Suite: `HATH0R-CLI` Control Tower  
> Date: 2026-10-05

## 1. Role & Identity

`PhoenixManagerBot` is an autonomous control-tower bot responsible for orchestrating, diagnosing, and reporting telemetry analytics across Arize Phoenix instances for all suite Docker meshes (`hath0r`, `1-nation`, `bai`).

---

## 2. Capabilities & Interface

### Core Methods
- `start_phoenix(group: str = "hath0r", detach: bool = True) -> Dict[str, Any]`
  - Launches container and verifies port availability.
- `stop_phoenix(group: str = "hath0r") -> Dict[str, Any]`
  - Stops container cleanly.
- `check_status(group: str = "hath0r", custom_endpoint: Optional[str] = None) -> Dict[str, Any]`
  - Probes edge and direct health endpoints (`http://localhost:38000/phoenix/`, `http://localhost:58000/phoenix/`, etc.).
- `get_projects(group: str = "1-nation") -> List[Dict[str, Any]]`
  - Queries active OpenInference projects and span distributions directly from SQLite `/data/phoenix.db`.
- `get_cost_summary(group: str = "1-nation") -> Dict[str, Any]`
  - Aggregates prompt and completion tokens and FinOps USD costs.

---

## 3. CLI Command Binding

Bound to `hath0r phoenix` CLI group:
```bash
hath0r phoenix status [--group <hath0r|1-nation|bai>] [--json]
hath0r phoenix up [--group <hath0r|1-nation|bai>] [--detach]
hath0r phoenix down [--group <hath0r|1-nation|bai>]
hath0r phoenix projects [--group <hath0r|1-nation|bai>] [--json]
hath0r phoenix costs [--group <hath0r|1-nation|bai>] [--json]
hath0r phoenix ui [--group <hath0r|1-nation|bai>] [--edge/--direct]
hath0r phoenix evals [--suite <suite-id>]
```
