# Procedure: FMEA

> **Procedure ID**: `PR-FMEA-001` · **Owning Bot**: `fmea-bot`

1. `hath0r fmea init <process>` for each factory workflow worth analysing.
2. Review the seeded rows: fix steps, adjust ratings, add process-specific rows with `hath0r fmea add`.
3. `hath0r fmea score <process>` refreshes occurrence from data and ranks rows.
4. `hath0r fmea sync-issues <process>` files an issue per H row (or link an existing one: `hath0r fmea update ... --issue N`).
5. When an action lands, `hath0r fmea update <process> <row> -d <new> --action "<what>"`, then rescore.
6. `hath0r fmea export <process>` puts M and H rows into AgentGraph (`hath0r agentgraph sync`).
7. The `fmea-review` workflow repeats steps 3-6 weekly.
