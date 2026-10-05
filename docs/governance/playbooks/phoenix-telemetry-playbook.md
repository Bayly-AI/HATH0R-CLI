# Arize Phoenix Telemetry Operational Playbook

> Artifact: **Playbook** · Member of **Artifact Hexad** (`CR-CLI-FEATURE-STANDARD-001`)  
> Suite: `hath0r-opensource` / `bayly-ai` / `1-nation`  
> Date: 2026-10-05

## 1. Overview & Triggers

This operational playbook provides step-by-step guidance for diagnosing and resolving common observability issues:
- **Play 1**: Spans not appearing in Arize Phoenix UI
- **Play 2**: HTTP 415 Unsupported Media Type during trace ingestion
- **Play 3**: FinOps Token or Cost Spikes
- **Play 4**: Missing Project Names / Spans Routed to "default"

---

## 2. Plays

### Play 1: Spans Not Appearing in UI
1. **Check Phoenix Server Health**:
   ```bash
   hath0r phoenix status --group <target-group>
   ```
2. **Verify Client Tracer Initialization**:
   Ensure `init_phoenix_provider()` or `OTLPSpanExporter` was executed during application startup.
3. **Verify Host Port Fallback**:
   If executing outside Docker, confirm endpoint resolves to `http://localhost:58000/phoenix/v1/traces` or `http://localhost:38000/phoenix/v1/traces` rather than container DNS names (`1NPHOENIX`).
4. **Inspect SQLite Database**:
   ```bash
   docker exec HATH0R-Phoenix /usr/bin/python3.13 -c "import sqlite3; con=sqlite3.connect('/data/phoenix.db'); print(con.cursor().execute('SELECT count(*) FROM spans').fetchone()[0])"
   ```

### Play 2: HTTP 415 Unsupported Media Type
- **Root Cause**: Arize Phoenix native OTLP endpoint accepts HTTP Protobuf (`Content-Type: application/x-protobuf`).
- **Remedy**: Ensure client uses `opentelemetry.exporter.otlp.proto.http.trace_exporter.OTLPSpanExporter` (HTTP Protobuf exporter) rather than raw JSON POSTs.

### Play 3: FinOps Token or Cost Spikes
1. **Inspect Costs via CLI**:
   ```bash
   hath0r phoenix costs --group 1-nation
   ```
2. **Filter Expensive Spans in Phoenix UI**:
   - Open `hath0r phoenix ui --group 1-nation`
   - Sort traces table by `Total Tokens` descending.
   - Inspect the prompt and completion attributes in the span drawer to locate non-optimized DSPy chains or runaway agent loops.
3. **Enable Tiered Routing & Semantic Caching**:
   - Activate `SemanticCache` in `src/hath0r_engine/gateway/` to memoize repetitive prompt completions.

### Play 4: Spans Routed to "default" Project
1. **Verify Project Headers**:
   Ensure the OTLP exporter specifies `headers={"x-phoenix-project-name": "<project_id>"}`.
2. **Verify Resource Attributes**:
   Ensure `Resource.create({"service.name": "<project_id>", "openinference.project.name": "<project_id>"})` is attached to the `TracerProvider`.
