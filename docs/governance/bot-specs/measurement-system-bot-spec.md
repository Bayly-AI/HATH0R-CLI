# Bot Specification: `MeasurementSystemBot` (`measurement-system-bot`)

> **Bot ID**: `measurement-system-bot`  
> **Class**: `hath0r_cli.bots.measurement_system_bot.MeasurementSystemBot`  
> **Level 2 CLI**: `hath0r evals msa run|report`  
> **Level 1 MCP**: `evals_msa_report` (HATH0R-MCP, read-only)

## Responsibilities
1. Load and validate the panel (`cfg/evals/msa-panel.yaml`): at least 2 parts, unique ids, `expected: pass|fail`, at least one seeded defect.
2. Build each part in a fresh git workspace with memory initialised, then measure it with the canonical `TaskEvaluatorBot`.
3. Compute crossed Gage R&R (`hath0r_cli.qa.msa.gage_rr_anova`) and attribute agreement; fail on any target miss.
4. Persist `.hath0r/evals/msa/<study_id>.json` and `latest.json` atomically; compound an `msa:<study_id>` fact node.
5. Provide `report()` with `qualified_now` from `TaskEvaluatorBot.measurement_status()`.

## Actions
| Action | Method | Notes |
|---|---|---|
| `run-study` | `run_study(panel_path, replicates=3, dry_run=False)` | `success` is true only when the study passes |
| `report` | `report()` | Latest study without raw measurements |
| `status` | `status()` | Health and whether a study exists |
