# Procedure: Root cause analysis

> **Procedure ID**: `PR-RCA-001` · **Owning Bot**: `root-cause-bot`

1. Failed eval gates are tagged automatically (end-of-task `root-cause-bot gate` step, and on every Pareto run).
2. Tag CI, red-team and Andon failures by hand: `hath0r rca tag --source ci --ref <run> --summary "..."`.
3. Retag anything `unclassified` with `--category`.
4. Monthly: `hath0r rca pareto --since 30d`. For the top cause, open a DMAIC issue from the template.
5. `hath0r rca fishbone <issue> --cause ...` to collect candidate causes, then `hath0r rca why <issue>` (3 to 5 answers).
