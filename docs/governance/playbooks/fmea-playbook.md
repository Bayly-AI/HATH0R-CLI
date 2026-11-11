# Playbook: FMEA

> **Playbook ID**: `PB-FMEA-001` · **Owning Bot**: `fmea-bot`

| Situation | Play |
|---|---|
| H from severity 9-10 | Lower occurrence (a poka-yoke guard) or detection (a gate); severity rarely moves |
| High detection rating (7+) | Nothing catches it: add a bot step, an eval check or an Andon `stop` |
| Occurrence is a seed estimate | Give the row a `--signal` so data replaces the guess |
| Row mapped to `workflow` | No step matches; the missing step is often the fix |
| Score did not drop after a fix | Occurrence only drops when the data does; re-rate detection for new gates |
