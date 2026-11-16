# Workflow: Judge calibration (`cfg/factories/judge-calibration-factory.yaml`)

> **Workflow ID**: `cfg/factories/judge-calibration-factory.yaml` · **Owning Bots**: `judge-calibration-bot`, `task-evaluator-bot`

1. **`smoke` (`judge-calibration-bot`)**: two items per level, one replicate, dry run. Abort on any judge error.
2. **`calibrate` (`judge-calibration-bot`)**: full study, MFRM fit and per-level decisions, saved with the registry.
3. **`report` (`judge-calibration-bot`)**: latest study; scorecards then use the registry (`task-evaluator-bot`).
