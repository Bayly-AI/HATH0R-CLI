# Procedure: Eval measurement system analysis

> **Procedure ID**: `PR-EVAL-MSA-001` · **Owning Bot**: `measurement-system-bot`

1. Run a study whenever `cfg/evals/task-eval.json` changes (weights, thresholds, tier4, judge) or a tier's code changes.
2. `hath0r evals msa run` replays every panel part through `TaskEvaluatorBot` in a fresh workspace, 3 replicates per operator.
3. The study is saved to `.hath0r/evals/msa/<study_id>.json` and `latest.json`, and compounded as an `msa:<study_id>` fact.
4. If the study fails, the gauge is not qualified: fix the tier that missed the defect or caused the variation, then rerun.
5. To add a part, add a fixture change under `cfg/evals/msa-fixtures/` and a row in `cfg/evals/msa-panel.yaml`
   with `expected: pass|fail`. Every new failure mode found in production should become a seeded defect.
