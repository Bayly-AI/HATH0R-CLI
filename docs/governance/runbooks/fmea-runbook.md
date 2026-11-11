# Runbook: FMEA

> **Runbook ID**: `RB-FMEA-001` · **Owning Bot**: `fmea-bot`

```bash
hath0r fmea init end-of-task
hath0r fmea score end-of-task
hath0r fmea report --top 10
hath0r fmea add end-of-task --step run-eval --mode "..." --effect "..." --cause "..." -s 8 -o 3 -d 5 --signal tier:adversarial
hath0r fmea update end-of-task EOT-13 -d 3 --action "eval step marked andon: stop"
hath0r fmea update end-of-task EOT-13 --issue 596
hath0r fmea sync-issues end-of-task --dry-run
hath0r fmea export end-of-task && hath0r agentgraph sync
```

Signals: `eval_fail_rate`, `tier:<deterministic|trajectory|adversarial|goal_alignment>`, `andon:<source>`, `msa:missed_defects`,
`gate:escape` (share of `gate: verified` steps that ran unverified, from `.hath0r/state/gates/events.jsonl`) and
`clarity:unasked` (share of task starts whose issue lacked acceptance criteria and went ahead without a decision, from
`.hath0r/state/clarity/events.jsonl`). The two ledger signals need 20 samples before they replace a hand rating.
Change a row's signal with `hath0r fmea update <process> <row> --signal <signal>`.
State `.hath0r/fmea/<process>.yaml`; schema `contracts/hath0r-fmea-v1.schema.json`.

## Controls added for the first study (#596, #597, #598)

- A factory step marked `gate: verified` runs only when `hath0r evals verify` passes and `hath0r andon status`
  shows no stop. The workflow executor enforces it, fails closed, and logs every decision to the gate ledger.
  `end-of-task` gates `merge-pr` and `announce-complete`, and runs the eval with tests before the PR is opened.
  `pr-lifecycle` gates `document-merged-prs`; Dependabot merges rely on CI and are refused when no checks report.
- `start-of-task` runs `decision-radar-bot clarify-issue` after the issue is verified. When the issue has no
  acceptance section with at least one item, it raises a decision and the step fails until the issue is clarified.
