# Checklist — OpenTelemetry Runtime Tracing (#117)

- [ ] `cfg/observability/otel.json` loaded and validated
- [ ] Tracer provider initialized with `service.name: hath0r-cli`
- [ ] Root spans created for top-level commands
- [ ] Child spans created for factory steps and bot dispatches
- [ ] Spool telemetry events include active `trace_id` and `span_id`
- [ ] Safe fallback when `opentelemetry` is unconfigured or collector offline
- [ ] No secrets leaked in span attributes
- [ ] Unit tests pass with 100% assertion coverage
