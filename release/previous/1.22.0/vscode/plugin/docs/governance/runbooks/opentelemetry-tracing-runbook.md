# Runbook — OpenTelemetry Runtime Tracing Ops (#117)

> Product: `Bayly-AI/HATH0R-CLI` · Control Tower · Issue #117

## Troubleshooting Tracing

### 1. Spans Not Exported to Remote Collector
- Verify collector endpoint in `OTEL_EXPORTER_OTLP_ENDPOINT` (defaults to `http://localhost:4318`).
- Check collector reachability via `curl -v http://localhost:4318/v1/traces`.
- If using authorization headers, confirm `OTEL_EXPORTER_OTLP_HEADERS` is set in `/Users/raybayly/Development/.credentials/<service>/.env`.

### 2. Tracing Inadvertently Slowing Down CLI
- By default, CLI initializes tracing with non-blocking simple or in-memory handlers when offline.
- To disable tracing entirely during local development or scripting, run:
  ```bash
  export HATH0R_OTEL_ENABLED=false
  # or
  export OTEL_SDK_DISABLED=true
  ```

### 3. Correlating Spool Records with Traces
- Open `.hath0r/spool/telemetry-YYYYMMDD.jsonl`.
- Look for `"trace_id"` and `"span_id"` keys in the JSON records.
- Query your APM / Jaeger / OTel collector using the exact `trace_id` hex string.
