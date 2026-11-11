# Strategy: Statistical process control for Hath0r (WS2/WS3, #586, #587)

> **Strategy ID**: `ST-SPC-001` · **Owning Bot**: `spc-monitor-bot`

A single eval tells you whether one task passed. A control chart tells you whether the process that produces
tasks has changed. Hath0r charts its own signals (R_task, each tier, eval duration, tokens, cost, latency)
using the NIST/SEMATECH methods: I-MR limits, Western Electric rules 1-4, EWMA (lambda 0.2) and tabular CUSUM.

- Capability is R_task Cpk against the eval threshold (LSL 0.80, one-sided). The goal is R_task as close to 1.0 as possible.
- Validated decision (2026-11-11): signals and Cpk below 1.33 are **warnings**. `capability.mode: block` in
  `thresholds.json` upgrades them to a blocking gate that also pulls the Andon cord.
- #608: the default is `capability.mode: auto`. It warns while limits are provisional and blocks (pulling Andon)
  once a metric has 20 points. `warn` and `block` keep their meaning.
- #608: eval metrics are charted only from scorecards with the current judge fingerprint. Points scored by a
  different gauge are not comparable, so a judge change starts a new chart.
- Limits from fewer than 20 points are provisional. After a deliberate process change, freeze new limits
  from recent points (`hath0r spc baseline --recent`).
