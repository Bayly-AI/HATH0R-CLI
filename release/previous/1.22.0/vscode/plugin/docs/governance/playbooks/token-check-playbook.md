# Token Check Workflow Playbook

> ID: `token-check-playbook`  
> Control tower: `Bayly-AI/HATH0R-CLI` · Issue track: #308  
> Owner: `@somesayray`  
> Updated: 2026-10-03  

---

## Overview

The **Token Check Workflow** (`token-check`) automates the retrieval, auditing, statistical analysis, and visual reporting of FinOps token telemetry across all agent interactions for user `raybayly` (or any specified user profile).

Whenever an operator or user requests **"token check"** or runs `hath0r finops tokens check`, this workflow executes:
1. Telemetry ledger parsing from `.hath0r/finops/token_telemetry.jsonl`.
2. 90-day trailing window aggregation (prompt tokens, completion tokens, USD cost).
3. Statistical distribution computation ($p_{50}, p_{95}, p_{99}$, mean, std dev).
4. Equal-width 10-bin histogram generation.
5. Model & tier cost allocation breakdown (`LIGHT`, `STANDARD`, `REASONING`).
6. Generative UI HTML artifact dashboard synthesis (`finops_token_histogram.html`).

---

## Execution Paths

### 1. Operator CLI Command
```bash
hath0r finops tokens check [--user <user_id>] [--days 90]
```

### 2. FastMCP Tool Integration
```json
{
  "tool": "hath0r_finops_token_check",
  "arguments": {
    "user_id": "raybayly",
    "days": 90
  }
}
```

---

## Output Artifacts

- **HTML Dashboard**: Saved to conversation/app artifact directory with `<agent-embed>` inline rendering.
- **Markdown Report**: Includes summary table, statistical metrics, ASCII histogram, and model breakdown.
