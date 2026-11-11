# Runbook: DMAIC

> **Runbook ID**: `RB-DMAIC-001` · **Owning Bot**: `dmaic-project-bot`

```bash
hath0r dmaic start 599 --ctq goal_alignment --target 0.97 --problem "Tier 4 cannot rank good work"
hath0r rca why 599 --problem "..." --because "..." --because "..." --because "..."
hath0r dmaic analyze 599
hath0r dmaic improve 599 --change "PR #NNN: per-tier evidence for Tier 4"
hath0r dmaic status 599
hath0r dmaic close 599
```

State `.hath0r/dmaic/<issue>.json`; schema `contracts/hath0r-dmaic-project-v1.schema.json`.
