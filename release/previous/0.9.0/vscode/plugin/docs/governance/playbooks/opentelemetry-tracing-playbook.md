# Playbook — OpenTelemetry Runtime Tracing Setup (#117)

> Product: `Bayly-AI/HATH0R-CLI` · Control Tower · Issue #117

## Practical Decision Guidance

1. **Local Development (No Collector)**:
   - Default behavior: Tracing initializes and records spans in memory / local span processor.
   - Spooled events in `.hath0r/spool/` will generate valid `trace_id` and `span_id` without external network dependency.

2. **Integration / Staging Environments (With Collector)**:
   - Point `OTEL_EXPORTER_OTLP_ENDPOINT` at the staging OTLP collector (e.g. `http://otel-collector.internal:4318`).
   - CLI spans will automatically flow upstream alongside container and MCP telemetry.

3. **CI Environments**:
   - Trace generation remains active to verify telemetry pipeline health.
   - Set `HATH0R_OTEL_CONSOLE_EXPORT=false` to prevent cluttering CI test output.
