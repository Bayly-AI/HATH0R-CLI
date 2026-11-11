# Bot Specification: `FMEABot` (`fmea-bot`)

> **Bot ID**: `fmea-bot` · **Class**: `hath0r_cli.bots.fmea_bot.FMEABot`  
> **Level 2 CLI**: `hath0r fmea init|add|update|score|report|sync-issues|export` · **Level 1 MCP**: `fmea_query` (HATH0R-MCP, read-only)

| Action | Method | Notes |
|---|---|---|
| `init` | `init(process, factory=None, force=False)` | 14 MAST rows mapped to factory steps |
| `add` / `update` | `add(...)`, `update(process, row_id, ..., action, issue)` | Ratings validated 1-10 |
| `score` | `score(process, refresh=True)` | Occurrence from data signals; ranked by AP, S, RPN |
| `report` | `report(process=None, top=10)` | |
| `sync-issues` | `sync_issues(process, repo, min_priority="H", dry_run)` | Through `IssueManagerBot.create_issue` |
| `export` | `export_agentgraph(process, min_priority="M")` | Memory `concept` nodes ingested by AgentGraph |
| `review` | `review(process, repo, dry_run=True)` | Factory step |
