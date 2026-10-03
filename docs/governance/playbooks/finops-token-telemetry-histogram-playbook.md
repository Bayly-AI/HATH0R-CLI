# FinOps Token Telemetry and Histogram Analytics Playbook

## Overview
Operator playbook for diagnosing token cost anomalies, skewed prompt distributions, and ledger issues.

## Diagnostic Steps

### High Cost Spike Detected
1. Run histogram on `cost_usd`:
   ```bash
   hath0r finops tokens histogram --metric cost_usd --bins 10
   ```
2. Identify top users in `user_distribution`.
3. Filter user records:
   ```bash
   hath0r finops tokens list --user "<user>" --limit 20
   ```

### Skewed Prompt Tokens (Outlier Detection)
1. Run prompt tokens histogram:
   ```bash
   hath0r finops tokens histogram --metric prompt_tokens
   ```
2. Inspect P95 and P99 quantiles.
3. Review long prompt records to evaluate caching or context pruning opportunities.
