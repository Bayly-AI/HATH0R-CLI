# Arize Phoenix Telemetry Workflow Specification

> Artifact: **Workflow** · Member of **Artifact Hexad** (`CR-CLI-FEATURE-STANDARD-001`)  
> Suite: `hath0r-opensource` / `bayly-ai` / `1-nation`  
> Date: 2026-10-05

## 1. Workflow Summary

The Phoenix Telemetry Workflow coordinates continuous calibration (`CR-CICCCD-001`), live agent tracing, and evaluation feedback loops.

```mermaid
sequenceDiagram
    autonumber
    actor Developer as Developer / CI
    participant CLI as HATH0R CLI
    participant Engine as Hath0r Cognitive Engine
    participant Proxy as Nginx Edge Proxy
    participant Phoenix as Arize Phoenix

    Developer->>CLI: hath0r cicccd calibrate
    CLI->>Engine: Run evaluation test suite
    Engine->>Proxy: POST /v1/traces (Eval metrics & benchmarks)
    Proxy->>Phoenix: Ingest OTLP Spans
    Phoenix-->>Proxy: 200 OK (Indexed in SQLite)
    CLI->>Phoenix: Query eval thresholds & drift
    Phoenix-->>CLI: Return calibration report
    CLI-->>Developer: Output pass/fail Quality Gate
```

---

## 2. Pipeline Integration Points

1. **Pre-Commit / Local Testing**:
   - `pytest tests/unit/test_phoenix_observability.py`
   - Validates that tracer provider successfully generates OTLP payload without network errors.
2. **CI Promotion Gate (`CR-BAI-001`)**:
   - Every promotion from `development` to `testing` executes evaluation suites.
   - Evaluator spans (`StatutoryFaithfulness`, `NeutralityTone`, `CitizenReadability`) are verified against quality gate minimum thresholds.
3. **Production Runtime**:
   - Live client requests route through `AIGatewayClient` with dynamic FinOps token and latency tracking.
