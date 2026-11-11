# Workflow: Root cause Pareto (`cfg/factories/rca-pareto-factory.yaml`)

> **Workflow ID**: `cfg/factories/rca-pareto-factory.yaml` · **Owning Bot**: `root-cause-bot` · monthly

1. **`auto-tag`**: tag every failed gate in the eval history (idempotent).
2. **`pareto`**: 30-day Pareto by category to `.hath0r/rca/pareto-latest.json`.

`end-of-task-factory.yaml` also runs `root-cause-bot gate` after the eval step.
