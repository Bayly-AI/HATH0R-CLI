# Runbook: Root cause analysis

> **Runbook ID**: `RB-RCA-001` · **Owning Bot**: `root-cause-bot`

```bash
hath0r rca pareto --since 30d            # by category
hath0r rca pareto --since all --by gate
hath0r rca tag --source ci --ref 1234 --summary "docker network timeout" --category machine
hath0r rca fishbone 599 --problem "..." --cause "synthetic critic text" --category measurement
hath0r rca why 599 --problem "..." --because "..." --because "..." --because "..."
```

State `.hath0r/rca/tags.json`, `.hath0r/rca/<issue>.json`, `.hath0r/rca/pareto-latest.json`; schema `contracts/hath0r-rca-v1.schema.json`.
