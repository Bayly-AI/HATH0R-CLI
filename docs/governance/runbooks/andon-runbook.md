# Runbook: Andon

> **Runbook ID**: `RB-ANDON-001` · **Owning Bot**: `andon-bot`

```bash
hath0r andon status                         # exit 1 while a stop is active
hath0r andon raise --reason "manual stop"   # pull the cord by hand
hath0r andon ack andon-1a2b3c4d5e --by ray
hath0r andon clear andon-1a2b3c4d5e --note "fixed flaky fixture"
hath0r andon verify
```

In code: `AndonBot(cwd).raise_event(source=..., reason=..., severity="stop")`, `AndonBot(cwd).check()` raises
`AndonStop`. `AgentDAGRunner.execute_dag` returns `status: andon_stopped` (opt out per DAG with `"andon": false`).
`TokenTreeBudgetGuard(andon_cwd=...)` raises a stop when it trips. Schema: `contracts/hath0r-andon-event-v1.schema.json`.
