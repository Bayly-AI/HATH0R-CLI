# FinOps Token Telemetry and Histogram Analytics Procedure

## Scope
Standard procedure for recording, inspecting, and analyzing agent token distributions via Hath0r CLI.

## Ingestion Procedure
1. Execute `hath0r finops tokens record`:
   ```bash
   hath0r finops tokens record --prompt "<prompt>" --user "<user>" --tier <light|standard|reasoning>
   ```
2. Verify record creation in `.hath0r/finops/token_telemetry.jsonl`.

## Retrieval Procedure
1. Query interactions:
   ```bash
   hath0r finops tokens list --user "<user>" --limit 50
   ```
2. Output JSON for automated pipelines:
   ```bash
   hath0r -o json finops tokens list --limit 100
   ```

## Histogram Generation Procedure
1. Run distribution analysis:
   ```bash
   hath0r finops tokens histogram --metric prompt_tokens --bins 10
   ```
2. Filter by user or metric (`prompt_tokens`, `prompt_length_chars`, `total_tokens`, `cost_usd`).
