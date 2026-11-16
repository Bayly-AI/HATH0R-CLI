# Runbook: Judge calibration

Keys: put `ANTHROPIC_API_KEY=` in `~/Development/.credentials/anthropic/.env` and `JEV_API_KEY=` in
`~/Development/.credentials/jev/.env`. The bot loads them when the variables are unset. Values already in the
environment win, and `HATH0R_CREDENTIALS_DIR` overrides the folder. Run the preflight check first: it shows each
key's format class, never its value, and fails on a key of the wrong kind.

```sh
hath0r evals judges status --preflight                                 # keys present and of the right kind
hath0r evals judges calibrate --per-level 2 --replicates 1 --dry-run   # smoke
hath0r -o json evals judges calibrate > /tmp/studyb.json               # full run (cost capped by the panel)
hath0r evals judges calibrate --resume .hath0r/evals/judges/<id>.ratings.jsonl
hath0r evals judges report
hath0r evals judges status claude-opus --level L4
hath0r spc chart -m judge_severity@claude-opus:L4
```

Files: `.hath0r/evals/judges/<study_id>.json`, `<study_id>.ratings.jsonl`, `latest.json`, `registry.json`,
`ledger.jsonl` (SHA-256 hash chain of every live call; kept apart from the FinOps telemetry that Tier 2 reads).

Troubleshooting: `HTTP 404 model` means a model id in the panel is not available to the key; `JEV_API_KEY is
not set` means the key was not loaded into the study's shell; `<openrouter>` next to a JEV judge in the
preflight means `JEV_API_KEY` holds an OpenRouter key, not a jevai.org key; a judge with 25 failed calls is dropped and
listed under `errors`.
