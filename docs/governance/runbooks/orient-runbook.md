# Runbook: Orient Bot & CLI Operational Runbook

> Canonical Operational Runbook · Hath0r Agentic Framework  
> Updated: 2026-10-12 · Issue: #275 / CLI #463

## 1. System Overview

`OrientBot` (`hath0r orient`) services operator and autonomous agent requests for complete repository orientation. It executes a 6-stage cognitive walkthrough, extracting AgentGraph rules, README architecture, AST code symbols, performance observability, and CCCD calibration before returning a dual-mode TUI/Markdown report.

---

## 2. Operator Execution Commands

### Run via Operator CLI
```bash
# Standard repository orientation
hath0r orient

# Orient a specific target repository path
hath0r orient --repo /path/to/repo

# Output in Markdown format (ideal for CI, logging, and piping)
hath0r orient --markdown

# Output as raw JSON payload matching schema contract
hath0r orient --json
```

### Run via Conversational Agent Trigger
When prompted in agent dialogue with `"orient"`, `"run orient"`, or `"orient repo"`, the agent executes the orient procedure and presents the structured report.

---

## 3. Failure Modes & Troubleshooting

| Symptom | Root Cause | Operator Action |
| :--- | :--- | :--- |
| `AgentGraph snapshot not found` | Repo has not run AgentGraph sync | Run `hath0r agentgraph sync` |
| `Calibration stale warning` | CCCD state older than 24 hours | Run `hath0r cicccd calibrate` |
| `TUI distorted` | Terminal lacks Unicode/ANSI support | Pass `--markdown` flag |
| `Unknown language in code scan` | Custom file extensions not in map | Added to generic language parser |
