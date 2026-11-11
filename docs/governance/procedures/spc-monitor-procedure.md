# Procedure: Statistical process control

> **Procedure ID**: `PR-SPC-001` · **Owning Bot**: `spc-monitor-bot`

1. Every `end-of-task` and `local-quality-gates` run calls `spc-monitor-bot gate` (`on_failure: continue`).
2. In warn mode, signals appear as `SPC_SIGNAL` warning diagnostics and in `.hath0r/spc/latest.json`.
3. When a signal appears, find its point in `hath0r spc chart -m <metric>` and look for an assignable cause
   (a config change, a new tier check, a dependency). Record it with `hath0r rca` when it is not obvious.
4. When the cause is a deliberate improvement, re-baseline: `hath0r spc baseline -m <metric> --recent`.
5. Do not re-baseline to make a real degradation disappear.
