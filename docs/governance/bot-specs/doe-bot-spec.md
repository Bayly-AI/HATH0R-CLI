# Bot Specification: `DoEBot` (`doe-bot`)

> **Bot ID**: `doe-bot`  
> **Class**: `hath0r_cli.bots.doe_bot.DoEBot`  
> **Level 2 CLI**: `hath0r optimize screen|rsm|bayes|confirm`, `hath0r cccd calibrate --strategy sequential`  
> **Level 1 MCP**: `hath0r_optimize_doe`

## Actions
| Action | Method | Notes |
|---|---|---|
| `screen` | `screen(ranges, responses=None, measure=None, fraction=0, replicates=3, alpha=0.05)` | 2^(k-p) design and main-effects ANOVA |
| `rsm` | `rsm(ranges, responses=None, measure=None, design="ccd", goal="maximize")` | CCD/BBD, quadratic fit, optimum and interval |
| `bayes` | `bayes(ranges, measure, n_trials=30)` | optuna TPE; CCD fallback without optuna |
| `confirm` | `confirm(study_id, observed)` | Compounds a `fact` node when confirmed |
| `sequential` | `sequential(ranges, measure, ...)` | screen, keep significant, rsm, confirm |
| `calibrate-sequential` | `calibrate_sequential(spec, measure_cmd=None)` | Factory step; spec `measure_cmd` is the default |
| `status` | `status()` | Lists studies and whether optuna is installed |

## Outputs
`.hath0r/optimize/<study_id>.json`, MLflow runs (best effort), memory node `fact:doe:<study_id>`.

## Failure modes
Invalid ranges or response counts raise `ValueError` (CLI `DOE_INVALID_INPUT`, exit 2). A failing
measurement command stops the study with its stderr.
