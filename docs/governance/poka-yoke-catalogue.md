# Poka-yoke catalogue (WS5, #583)

> Mistake-proofing guards in the Hath0r CLI. Each guard stops a known error at the point where it would
> enter the system, instead of finding it later in review. Owner: the bot named in each row.

| Id | Guard | Where | Stops | Owning bot |
|---|---|---|---|---|
| PY-01 | Incomplete orthogonal-array experiments raise `IncompleteExperimentError` | `cccd/taguchi_optimizer.py` | Missing runs silently padded with invented data | `taguchi-bot` |
| PY-02 | `--allow-partial` analyses only measured runs and marks `partial: true` | `hath0r optimize taguchi`, MCP `hath0r_optimize_taguchi` | Partial experiments reported as complete | `taguchi-bot` |
| PY-03 | Factor level counts must equal the levels each array column tests | `TaguchiBot.generate_matrix` | Levels wrapped onto the wrong value (modulo mapping) or never tested | `taguchi-bot` |
| PY-04 | Levels for factors not in the design are rejected | `TaguchiBot.generate_matrix` | Typos in factor names silently ignored | `taguchi-bot` |
| PY-05 | Calibration history records `responses_source: measured|simulated` | `cccd/calibration_loop.py` | Simulated tuning data read as measurements (#595) | `cicccd-managing-bot` |
| PY-06 | Version drift between `VERSION`, `pyproject.toml`, `package.json` and the top `CHANGELOG.md` release fails preflight | `bots/quality.py::version_drift` | Releases with inconsistent version stamps | `preflight-bot` |
| PY-07 | Tier 1 `version_valid` is a hard 0/1 on drift or CHANGELOG misalignment | `TaskEvaluatorBot.tier1` | Missing version bump passing the eval gate (found by the WS1 gauge study) | `task-evaluator-bot` |
| PY-08 | Scorecards carry `measurement_qualified` and the judge fingerprint | `TaskEvaluatorBot.evaluate_task` | Trusting scores from an unqualified judge configuration | `measurement-system-bot` |
| PY-09 | Gage R&R needs a balanced study, at least 2 parts, 2 replicates and 1 seeded defect | `qa/msa.py`, `MeasurementSystemBot.load_panel` | Studies that cannot show discrimination | `measurement-system-bot` |
| PY-10 | SPC limits from fewer than 20 points are marked `provisional_*` | `qa/spc.py::chart` | Over-trusting control limits from a thin baseline | `spc-monitor-bot` |
| PY-11 | FMEA ratings outside 1-10 are rejected | `qa/fmea.py` | Unscoreable or inflated risk rows | `fmea-bot` |
| PY-12 | Andon stops are hash-chained and need an `ack` before `clear` | `AndonBot` | Silently clearing a line stop | `andon-bot` |

## Adding a guard
1. Put the check where the bad input first arrives, raise a `ValueError` subclass with a message that says how to fix it.
2. Add a row here and a test that proves the bad input is refused.
3. If the guard fires in a workflow, give it a `Diagnostic` code so it shows in `-o json` output.
