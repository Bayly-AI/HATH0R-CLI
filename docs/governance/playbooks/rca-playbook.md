# Playbook: Root cause analysis

> **Playbook ID**: `PB-RCA-001` · **Owning Bot**: `root-cause-bot`

| Pareto shows | Play |
|---|---|
| `unclassified` on top | Keywords miss your failures: retag by hand and extend `cause-categories.yaml` |
| `method` on top | A workflow step is missing or wrong: FMEA the factory |
| `measurement` on top | The gauge is suspect: `hath0r evals msa run` |
| `machine` on top | Infra noise: check Andon and CI history before changing code |
| A flat Pareto | No vital few yet; keep tagging until a pattern shows |
| 5 Whys stops at a person | Keep asking why the process let it happen |
