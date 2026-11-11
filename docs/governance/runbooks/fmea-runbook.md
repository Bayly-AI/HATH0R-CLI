# Runbook: FMEA

> **Runbook ID**: `RB-FMEA-001` · **Owning Bot**: `fmea-bot`

```bash
hath0r fmea init end-of-task
hath0r fmea score end-of-task
hath0r fmea report --top 10
hath0r fmea add end-of-task --step run-eval --mode "..." --effect "..." --cause "..." -s 8 -o 3 -d 5 --signal tier:adversarial
hath0r fmea update end-of-task EOT-13 -d 3 --action "eval step marked andon: stop"
hath0r fmea update end-of-task EOT-13 --issue 596
hath0r fmea sync-issues end-of-task --dry-run
hath0r fmea export end-of-task && hath0r agentgraph sync
```

Signals: `eval_fail_rate`, `tier:<deterministic|trajectory|adversarial|goal_alignment>`, `andon:<source>`, `msa:missed_defects`.
State `.hath0r/fmea/<process>.yaml`; schema `contracts/hath0r-fmea-v1.schema.json`.
