# Bot Specification: `AndonBot` (`andon-bot`)

> **Bot ID**: `andon-bot`  
> **Class**: `hath0r_cli.bots.andon_bot.AndonBot`  
> **Level 2 CLI**: `hath0r andon status|raise|ack|clear|verify`  
> **Level 1 MCP**: `andon_status` (HATH0R-MCP, read-only)

## State
`.hath0r/state/andon/events.jsonl`: append-only, SHA-256 hash-chained (same scheme as the FinOps token ledger).

## Actions
| Action | Method | Notes |
|---|---|---|
| `raise-event` | `raise_event(source, reason, severity="stop", workflow_id, step_id, details)` | Stops are routed to the Decision Radar |
| `ack` | `ack(event_id, by, note)` | |
| `clear` | `clear(event_id, by, note)` | Stops must be acknowledged first |
| `status` | `status()` | `stopped`, active events, ledger validity |
| `check` | `check()` | Raises `AndonStop` while stopped |
| `verify` | `verify()` | Hash chain check |
