# Bot Specification: `DMAICProjectBot` (`dmaic-project-bot`)

> **Bot ID**: `dmaic-project-bot` · **Class**: `hath0r_cli.bots.dmaic_project_bot.DMAICProjectBot`  
> **Level 2 CLI**: `hath0r dmaic start|analyze|improve|status|close`

| Action | Method | Notes |
|---|---|---|
| `start` | `start(issue, ctq, problem, target, goal)` | Define + Measure (SPC baseline) |
| `analyze` | `analyze(issue)` | Needs a 5 Whys from `root-cause-bot` |
| `improve` | `improve(issue, change)` | Marks the data point where the change landed |
| `control` | `control(issue)` | Post-change chart; `ready_to_close` |
| `close` | `close(issue)` | Refused until 20 in-control points after the change |
| `status` | `status(issue=None)` | |
