# Token Check Workflow Runbook

> ID: `token-check-runbook`  
> Control tower: `Bayly-AI/HATH0R-CLI` · Issue track: #308  
> Category: FinOps Ops & Day-2 Management  

---

## Operational Diagnostic Steps

If `hath0r finops tokens check` reports no telemetry records or errors:

1. **Verify Ledger Existence**:
   ```bash
   ls -la .hath0r/finops/token_telemetry.jsonl
   ```
2. **Re-seed Telemetry Sample** (if ledger missing):
   ```bash
   hath0r finops tokens record --prompt "test prompt" --user raybayly
   ```
3. **Inspect Ledger Syntax**:
   ```bash
   tail -n 10 .hath0r/finops/token_telemetry.jsonl
   ```
4. **Run Preflight & Unit Tests**:
   ```bash
   python3 -m pytest tests/unit/test_token_check_bot.py
   ```
