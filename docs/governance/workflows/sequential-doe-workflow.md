# Workflow: Sequential DoE calibration (`cfg/factories/cccd-4h-calibration-factory.yaml`)

> **Workflow ID**: `cccd-sequential-doe` · **Owning Bots**: `doe-bot`, `cicccd-managing-bot`, `taguchi-bot`

1. **`sequential` (`doe-bot calibrate-sequential`)**: reads `cfg/cccd/doe-spec.yaml`, screens the factors,
   fits a response surface on the significant ones and runs the confirmation. `on_failure: abort`,
   `andon: warn`. The step refuses while the spec has no `measure_cmd`.
2. The confirmed optimum is compounded as `fact:doe:<study_id>`.

The same factory keeps the `cccd-4h-calibration` freshness workflow (every 4 hours).
Acceptance test: the confirmation run lands inside the predicted interval.
