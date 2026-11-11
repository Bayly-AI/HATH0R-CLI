# Runbook: Eval measurement system analysis

> **Runbook ID**: `RB-EVAL-MSA-001` · **Owning Bot**: `measurement-system-bot`

```bash
hath0r evals msa run                      # full study, saved and compounded
hath0r evals msa run --dry-run            # compare a candidate config without saving
hath0r evals msa run --replicates 5       # tighter repeatability estimate
hath0r evals msa report                   # latest study + whether the current judge is qualified
hath0r -o json evals msa report           # machine-readable
hath0r evals run && hath0r -o json evals status   # scorecards include measurement_qualified
```

To compare a candidate judge setting, add `config:` overrides to the operators in a copy of the panel, for example
`{id: clamp-on, config: {tier4: {clamp: true}}}`, and run `hath0r evals msa run --panel <copy> --dry-run`.
Schema: `contracts/hath0r-msa-study-v1.schema.json`.
