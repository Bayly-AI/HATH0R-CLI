# Bot Specification: `RootCauseBot` (`root-cause-bot`)

> **Bot ID**: `root-cause-bot` · **Class**: `hath0r_cli.bots.root_cause_bot.RootCauseBot`  
> **Level 2 CLI**: `hath0r rca tag|pareto|fishbone|why`

| Action | Method | Notes |
|---|---|---|
| `tag` | `tag(source, ref, summary, category=None, gate=None, issue=None)` | Keyword classification unless a category is given |
| `auto-tag` | `auto_tag()` | Every blocking reason of every failed scorecard |
| `pareto` | `pareto(since_days=30, by="category"|"gate"|"source")` | Vital few to 80% |
| `fishbone` | `fishbone(issue, problem, category, cause)` | |
| `why` | `why(issue, problem, whys, root_cause, category)` | 3-5 answers; compounds an insight node |
| `gate` | `gate()` | Workflow step |
