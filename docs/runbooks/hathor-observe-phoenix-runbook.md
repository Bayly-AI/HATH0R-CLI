# Runbook: Hath0r CLI Arize Phoenix Commands & Telemetry

> **Canonical Operator Runbook** for using Hath0r CLI to manage and inspect Arize Phoenix.

## 1. Operator Commands

```sh
# Check Phoenix health status
hath0r phoenix status

# Start Phoenix container locally
hath0r phoenix up

# Stop Phoenix container
hath0r phoenix down

# Open Phoenix web console
hath0r phoenix ui

# Inspect evaluation benchmarks
hath0r phoenix evals
```

## 2. JSON Automation Mode

```sh
hath0r phoenix status --json
hath0r phoenix evals --json
```
