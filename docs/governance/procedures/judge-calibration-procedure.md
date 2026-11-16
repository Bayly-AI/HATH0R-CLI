# Procedure: Run a judge calibration (Study B)

1. Edit `cfg/evals/judge-panel.yaml`: enable the judges to calibrate, mark anchors (`truth`, human raters),
   set the budget cap (`budget.max_usd`, the approved exception) and prices.
2. Make API keys available in the shell that runs the study (`ANTHROPIC_API_KEY`, `JEV_API_KEY`), loaded from
   `~/Development/.credentials/<service>/.env`. Never commit or print them.
3. Smoke test: `hath0r evals judges calibrate --per-level 2 --replicates 1 --dry-run`. Every judge must show
   zero errors.
4. Run: `hath0r -o json evals judges calibrate > study.json`. Resume an interrupted run with
   `--resume .hath0r/evals/judges/<study_id>.ratings.jsonl`.
5. Review `hath0r evals judges report` and `hath0r evals judges status`. Verify the call ledger is valid
   (`ledger.valid` in the study).
6. If an LLM judge is used by the eval pipeline, pin `judge_calibration.calibration_id` in
   `cfg/evals/task-eval.json` and rerun Study A (`hath0r evals msa run`), because the judge fingerprint changed.
