# Playbook: Statistical process control

> **Playbook ID**: `PB-SPC-001` · **Owning Bot**: `spc-monitor-bot`

| Signal | Meaning | Play |
|---|---|---|
| Rule 1 (one point beyond 3 sigma) | A single unusual task | Read that scorecard's `blocking_reasons` and tier scores |
| Rule 4 (8 in a row on one side) or EWMA/CUSUM | The process mean has shifted | Find the change that landed at the start of the run; re-baseline only if it was intended |
| Every point after the baseline flagged, sigma 0 | Baseline had no variation (for example the clamped era) | `hath0r spc baseline --recent` once the new process has 20 points |
| Low Cpk with no signals | Process is stable but too close to the 0.80 threshold | Improvement project: `hath0r dmaic start` |
| Cost or token signals | Spend pattern changed | `hath0r finops tokens histogram` to see which agent |
