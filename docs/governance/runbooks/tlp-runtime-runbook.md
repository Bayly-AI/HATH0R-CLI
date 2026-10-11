# Runbook: TLP Runtime & FinOps Operations

> Artifact: **Runbook** · Member of **Artifact Hexad** (`CR-CLI-FEATURE-STANDARD-001`)  
> Identity: `tlp-runtime-runbook`  
> Suite: `HATH0R-CLI` Control Tower  
> Issue Reference: Bayly-AI/HATH0R-CLI#426  
> Date: 2026-10-11

## 1. Operational Scope

This runbook covers operational maintenance, worker pool sizing, token budgeting, and FinOps metrics tracking for the TLP execution runtime.

---

## 2. Standard Operations

### Worker Pool Configuration
Default worker pool concurrency is set to 4. For high-throughput CI environments:
```bash
# High concurrency pool for multi-package testing
hath0r tlp run --plan dag.json --parallel --max-workers 8
```

### Token Tree Budgeting
Each worker thread allocates an isolated `ThreadContext` with a default `token_budget` of 25,000 tokens. Total cost across threads is tracked at `$0.002` per 1k tokens.

### Health & Preflight Inspection
Prior to large parallel runs, verify local system readiness:
```bash
hath0r doctor --verbose
hath0r tlp --help
```
