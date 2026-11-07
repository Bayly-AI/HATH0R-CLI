# FinOps Token Telemetry and Histogram Analytics Runbook

## Maintenance & Ledger Rotation
- **Storage Path**: `.hath0r/finops/token_telemetry.jsonl`
- **Format**: JSON Lines, 1 record per line.
- **Rotation Frequency**: Monthly or when exceeding 100MB.
- **Backup Command**:
  ```bash
  cp .hath0r/finops/token_telemetry.jsonl .hath0r/finops/token_telemetry_$(date +%Y%m%d).jsonl
  ```

## Health Metrics
- Query latency under 100ms for 10,000 records.
- JSON validity verified during ingestion.
