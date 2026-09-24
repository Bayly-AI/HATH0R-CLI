# Runbook — OTel ops

## No spans
- Check `OTEL_EXPORTER_OTLP_ENDPOINT` and collector health.
- Confirm sampler not dropping all (`OTEL_TRACES_SAMPLER_ARG`).

## Auth failures to collector
- Rotate token in credentials env only; never commit headers.
