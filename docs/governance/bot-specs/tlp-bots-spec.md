# Bot Specification: TLP Subsystem Bots

> Artifact: **Bot Specification** · Member of **Artifact Hexad** (`CR-CLI-FEATURE-STANDARD-001`)  
> Identity: `tlp-bots-spec`  
> Suite: `HATH0R-CLI` Control Tower  
> Issue Reference: Bayly-AI/HATH0R-CLI#426  
> Date: 2026-10-11

## 1. Overview

This specification details the architecture, public methods, and responsibilities of the three TLP bots residing in `src/hath0r_cli/bots/`:
1. `TaskLevelPlannerBot` (`task_level_planner_bot.py`)
2. `ThreadLevelParallelismBot` (`thread_parallelism_bot.py`)
3. `TemporalLogicPlannerBot` (`temporal_logic_planner_bot.py`)

---

## 2. Bot Interfaces

### `TaskLevelPlannerBot`
- **Role**: Decomposes natural language objectives into structured Task DAGs and handles dynamic replanning.
- **Key Methods**:
  - `create_plan(goal: str, context: Optional[Dict[str, Any]] = None) -> TaskExecutionDAG`: Heuristically decomposes goals into archetypes.
  - `topological_sort(dag: TaskExecutionDAG) -> List[List[str]]`: Computes execution tiers.
  - `detect_cycles(dag: TaskExecutionDAG) -> Tuple[bool, List[str]]`: Detects cyclic graph loops using Kahn's algorithm.
  - `replan_on_failure(dag: TaskExecutionDAG, failed_node_id: str, error_message: str) -> TaskExecutionDAG`: Injects remediation node and rewires dependencies.
  - `export_mermaid(dag: TaskExecutionDAG) -> str`: Renders Mermaid flowchart syntax.

### `ThreadLevelParallelismBot`
- **Role**: Dispatches independent task nodes concurrently across isolated thread contexts.
- **Key Methods**:
  - `run_parallel_dag(dag: TaskExecutionDAG, max_workers: int = 4, timeout_per_step: int = 60, executor: Optional[Callable] = None) -> Dict[str, Any]`: Executes tiers with fan-out / fan-in barriers.
  - `execute_node_thread(node: TaskNode, executor: Callable, timeout: int) -> ThreadExecutionRecord`: Runs an isolated thread with `ThreadContext` tracking.

### `TemporalLogicPlannerBot`
- **Role**: Compiles governance rules into Deterministic Finite Automata (DFA) and formally verifies execution trajectories.
- **Key Methods**:
  - `verify_trace(trace: List[str], policy_name: str = "all") -> Dict[str, Any]`: Evaluates trace against `cr-bai-001`, `cr-hathor-init-001`, and `cr-cicccd-001`.
  - Built-in DFAs:
    - `CR-BAI-001`: Promotion Path (`local` -> `development` -> `testing` -> `staging` -> `master`).
    - `CR-HATH0R-INIT-001`: Playbook & Runbook before Scaffolding.
    - `CR-CICCCD-001`: Calibration before Release/Deploy.

---

## 3. CLI Command Surface

The bots are surfaced under the `hath0r tlp` command group:
```bash
hath0r tlp plan --goal "<text>" [--format text|json|mermaid] [--output-file <file>]
hath0r tlp run [--goal "<text>"] [--plan <file>] [--parallel/--sequential] [--max-workers <N>]
hath0r tlp verify [--trajectory "<csv>"] [--plan <file>] [--policy all|cr-bai-001|cr-hathor-init-001|cr-cicccd-001]
```
