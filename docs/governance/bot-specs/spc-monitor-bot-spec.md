# Bot Specification: `SPCMonitorBot` (`spc-monitor-bot`)

> **Bot ID**: `spc-monitor-bot`  
> **Class**: `hath0r_cli.bots.spc_monitor_bot.SPCMonitorBot`  
> **Level 2 CLI**: `hath0r spc status|chart|baseline|capability`  
> **Level 1 MCP**: `quality_spc_status` (HATH0R-MCP, read-only)

## Inputs
- `.hath0r/evals/history/*.json` (R_task, tier scores, duration)
- `.hath0r/state/finops/token_ledger.jsonl` and `.hath0r/finops/token_telemetry.jsonl` (tokens, cost, latency)
- `thresholds.json` `capability` block

## Actions
| Action | Method | Notes |
|---|---|---|
| `status` | `status(metrics=None)` | Writes `.hath0r/spc/latest.json` |
| `chart` | `chart(metric, lam=None)` | Uses a frozen baseline when one exists |
| `baseline` | `baseline(metric, points, recent=False)` | Writes `.hath0r/spc/baselines.json` |
| `capability` | `capability(metric, lsl, usl)` | R_task defaults to LSL = eval `min_reward` |
| `gate` | `gate()` | Workflow step; raises an Andon stop in block mode |
