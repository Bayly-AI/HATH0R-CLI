# Strategy: Arize Phoenix Agent Observability & Evaluation Mesh

> **Architectural Strategy** · Part of `CR-CLI-FEATURE-STANDARD-001`

## 1. Architectural Principles

1. **Centralized Telemetry in CLI & Edge**: Phoenix collector is centrally hosted in the `1-nation` Docker network (`1NPHOENIX:4318`), surfaced via edge gateway `1NEDGE` (`/phoenix/`), and managed through Hath0r CLI (`hath0r phoenix [status|up|down|ui|evals]`).
2. **OpenInference Standard**: All agent bot executions, tool invocations, and guardrail validations emit OpenInference semantic conventions.
3. **Continuous Golden Dataset Benchmarking**: LLM-as-a-judge scorers run against versioned statutory benchmarks to detect quality regressions before PR merges.
