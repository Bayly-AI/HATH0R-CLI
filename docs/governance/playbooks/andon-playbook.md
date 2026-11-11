# Playbook: Andon

> **Playbook ID**: `PB-ANDON-001` · **Owning Bot**: `andon-bot`

| Source | Typical cause | Play |
|---|---|---|
| `token-tree-budget-guard` | Runaway agent tree | Inspect `hath0r finops budget check`; lower fan-out before clearing |
| `spc-monitor-bot` (block mode) | Process shift or low Cpk | `hath0r spc chart`, then `hath0r rca` if the cause is not obvious |
| A factory step with `andon: stop` | That step's check failed | Rerun the workflow with `-o json` and read the step error |
| `ANDON_LEDGER_TAMPERED` | Ledger edited by hand | Restore `.hath0r/state/andon/events.jsonl` from git; do not rewrite hashes |
