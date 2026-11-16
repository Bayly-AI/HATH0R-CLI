# Strategy: Eval measurement system analysis (WS1, #584)

> **Strategy ID**: `ST-EVAL-MSA-001` · **Owning Bot**: `measurement-system-bot` · **Rule**: `CR-TASK-EVAL-001`

## Why
`R_task` gates every task. If the eval pipeline itself is noisy or cannot tell good work from bad, the gate
is luck. Manufacturing solves this with Measurement System Analysis: qualify the gauge before trusting it.

## Position
- The eval pipeline is the gauge. Parts are fixture repositories with a known-good or seeded-defect change.
  Operators are independent evaluator instances (or candidate judge configurations).
- A crossed Gage R&R (AIAG ANOVA method) plus attribute agreement on pass/fail is the qualification test.
- Targets (validated 2026-11-11): %GRR <= 10%, ndc >= 5, zero missed defects, zero false alarms.
  Anything else is a failed study.
- A scorecard is `measurement_qualified` only while the latest passing study used the same judge fingerprint.
- Tier 4 clamping is off by default since the first study; scores now reflect raw signals.

## Level-stratified studies (v2, #612, epic #610)

Gage R&R alone assumes the gauge behaves the same at every complexity level. Panel v2 has eight parts at
each level L1 to L5 (`cfg/evals/complexity-levels.yaml`) and three operators, one of which rewrites each
change in a meaning-preserving form. The study adds, per level: %GRR, attribute agreement, bias against
the pooled bias (a level fails when the difference is significant and above 0.02), linearity of bias
across levels, and the verdict-flip rate of borderline parts. LLM judges are calibrated separately with a
many-facet Rasch model; see [judge-calibration-strategy.md](judge-calibration-strategy.md).
