# Playbook — OpenTelemetry setup

1. Copy `cfg/observability/otel.json` into the service repo.
2. Set `OTEL_EXPORTER_OTLP_ENDPOINT` from credentials env.
3. Wire SDK init at process start with required resource attributes.
4. Verify a test span reaches the collector.
5. Complete checklist `opentelemetry-adherence.md`.
