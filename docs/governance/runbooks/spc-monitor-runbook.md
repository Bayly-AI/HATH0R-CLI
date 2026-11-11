# Runbook: Statistical process control

> **Runbook ID**: `RB-SPC-001` · **Owning Bot**: `spc-monitor-bot`

```bash
hath0r spc status                          # every metric + R_task Cpk (warnings)
hath0r spc chart -m r_task                 # I-MR, EWMA, CUSUM, rule hits
hath0r spc chart -m cost_usd
hath0r spc capability                      # R_task Cpk/Ppk vs the eval threshold
hath0r spc capability -m latency_ms --usl 2000
hath0r spc baseline -m r_task --recent     # freeze limits from the last 20 points
hath0r quality local                       # now shows a Capability line
```

Settings live in `thresholds.json` under `capability`: `mode` (`warn`|`block`), `min_cpk_warn` (1.33),
`baseline_points` (20), `ewma_lambda` (0.2). Schema: `contracts/hath0r-spc-chart-v1.schema.json`.
