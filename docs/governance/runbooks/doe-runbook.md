# Runbook: Sequential design of experiments

> **Runbook ID**: `RB-DOE-001` · **Owning Bot**: `doe-bot`

```bash
hath0r optimize screen --factor temperature=0.1:0.7 --factor top_p=0.85:0.99     # print the design
hath0r optimize screen --spec screen.yaml                 # analyse: spec holds factors + responses
hath0r optimize screen --spec cfg/cccd/doe-spec.yaml --measure-cmd "<cmd>"        # measure as it goes
hath0r optimize rsm --spec rsm.yaml --design ccd           # spec holds the kept factors + responses
hath0r optimize bayes --spec cfg/cccd/doe-spec.yaml --measure-cmd "<cmd>" --trials 30   # needs the doe extra
hath0r optimize confirm <study_id> --observed 0.97,0.98,0.97
hath0r cccd calibrate --strategy sequential --spec cfg/cccd/doe-spec.yaml --measure-cmd "<cmd>"
```

A spec is YAML or JSON with `factors: {name: [low, high]}` and, to analyse, `responses:` (one list of
replicates per run, in design order). The measurement command reads one point as JSON on stdin and prints the measured response as the last line
of stdout. Studies are stored in `.hath0r/optimize/<study_id>.json`
(`contracts/hath0r-doe-study-v1.schema.json`) and logged to MLflow when it is reachable.
MCP: `hath0r_optimize_doe` (screen, rsm, confirm, status; never measures).
