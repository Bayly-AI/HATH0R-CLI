# Strategy — OpenTelemetry Runtime Tracing (#117)

> Product: `Bayly-AI/HATH0R-CLI` · Control Tower · Issue #117  
> Component: Runtime OpenTelemetry Instrumentation & Factory Trace Propagation

## Purpose

Establish distributed tracing and context propagation within the `hath0r` CLI and its underlying automation engines (`DynamicStepRunner`, Bot suite, and Docker Factory).

## Goals

1. **Deterministic Tracing**: Automatically initialize an OpenTelemetry tracer provider based on `cfg/observability/otel.json` or environment variables without failing CLI execution when unconfigured or offline.
2. **Step-Level Correlation**: Create root spans for top-level CLI commands and child spans for individual factory steps and bot dispatches, capturing execution duration, bot ID, action, retries, and failure status.
3. **Correlation IDs in Spool Logs**: Inject `trace_id` and `span_id` into `.hath0r/spool/telemetry-*.jsonl` events so spooled audit records directly correspond to distributed traces.
4. **Zero External Dependency Hard Stops**: If `opentelemetry` packages are unavailable or network exporters fail, the CLI degrades gracefully to no-op tracing without interruption to operator workflows.
5. **No Secret Leakage**: Comply with `never_commit_secrets`; OTLP headers and credentials must only be consumed via environment variable references or credential stores.

## Non-Goals

- Replacing the lightweight JSONL `.hath0r/spool` mechanism (traces complement the durable local append-only event spool).
- Mandating remote OTLP collectors for offline local development.
