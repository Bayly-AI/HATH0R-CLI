# Procedure — OpenTelemetry Runtime Tracing (#117)

> Product: `Bayly-AI/HATH0R-CLI` · Control Tower · Issue #117

## Normative Execution Steps

1. **Tracer Provider Initialization**:
   - At CLI startup, call `init_tracer()` from `hath0r_cli.telemetry`.
   - Read configuration from `cfg/observability/otel.json` or fallback defaults (`service_name="hath0r-cli"`, `namespace="hath0r-opensource"`, `environment="local"`).
   - If `opentelemetry` is available and enabled in configuration, bind TracerProvider with the configured Resource attributes.
   - If OTLP endpoint is supplied and reachable, configure standard batch/simple span processor; otherwise, default to in-memory/spooling exporter or no-op tracer.

2. **Command Span Lifecycle**:
   - Wrap top-level CLI execution in a root span `hath0r.<command_group>.<command>` (e.g., `hath0r.factory.run`, `hath0r.task.start`).
   - Tag span with attributes: `hath0r.cli.version`, `hath0r.product`, `hath0r.environment`, `hath0r.run_id`.

3. **Step Dispatch & Child Spans**:
   - In `DynamicStepRunner` / `execute_workflow`, open a child span `hath0r.step.<bot_id>.<action>`.
   - Propagate active span context to step execution.
   - Tag child span with `step.bot`, `step.action`, `step.policy`, `step.retries`, `step.dry_run`.
   - On step completion or abort, record exception/error details and set span status (`OK` or `ERROR`).

4. **Telemetry Event Spool Correlation**:
   - In `spool_telemetry_event()`, extract current active span context (`trace_id`, `span_id`).
   - Inject `trace_id` and `span_id` directly into the JSONL event envelope.
