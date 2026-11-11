# Playbook: Eval measurement system analysis

> **Playbook ID**: `PB-EVAL-MSA-001` · **Owning Bot**: `measurement-system-bot`

| Symptom | Likely cause | Play |
|---|---|---|
| `Seeded defects passed the gate: X` | A tier does not penalise that defect hard enough | Find the tier in `measurements[].tier_scores` for part X and make the check a hard gate (see PY-07) |
| `Known-good parts failed the gate: X` | Over-strict tier or a broken fixture | Run `hath0r evals run` inside a copy of the fixture and read `blocking_reasons` |
| `Verdict changed between replicates` | Non-deterministic tier (timing, ordering, network) | Pin the source of randomness; latency is the usual suspect |
| `%GRR` above 10% | Repeatability or reproducibility noise | Read `study_variation_pct`; repeatability means within-evaluator noise, reproducibility means operator bias |
| `ndc` below 5 | Parts too similar to tell apart | Add parts that span the score range, not just more of the same |
| `qualified_now: false` with a passing study | Judge configuration changed since the study | Rerun `hath0r evals msa run` |
