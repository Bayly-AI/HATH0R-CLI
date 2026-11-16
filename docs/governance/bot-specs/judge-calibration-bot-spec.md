# Bot Specification: `JudgeCalibrationBot` (`judge-calibration-bot`)

> **Bot ID**: `judge-calibration-bot`  
> **Class**: `hath0r_cli.bots.judge_calibration_bot.JudgeCalibrationBot`  
> **Level 2 CLI**: `hath0r evals judges calibrate|report|status`  
> **Level 1 MCP**: `evals_judge_calibration_report` (HATH0R-MCP, read-only)

## Responsibilities
1. Load `cfg/evals/judge-panel.yaml` and build judges: `truth`, `stub`, `anthropic`, `ollama`, `jev`, `import`.
2. Generate the item banks (`hath0r_cli.qa.judge_items`) and collect ratings with bounded concurrency,
   appending each rating to `<study_id>.ratings.jsonl` and each live call to the hash-chained ledger.
3. Stop at the budget cap and mark the study incomplete; drop a judge after repeated failures.
4. Fit the MFRM and apply the decision rules (`hath0r_cli.qa.rasch.calibrate`), with anchors as reference.
5. Persist the study, `latest.json` and `registry.json`; compound a `judges:<study_id>` fact node.
6. Answer `is_certified(judge, level, bank)` for scorecards and the MCP.

## Actions
| Action | Method | Notes |
|---|---|---|
| `calibrate` | `run_study(panel_path, banks, judges, replicates, per_level, dry_run, resume)` | `complete` is false when the cap stopped it |
| `report` | `report()` | Latest study |
| `status` | `status()` / `registry()` / `is_certified()` | Registry of certified levels |
