# HATH0R-GUIDE-050: Phase 1 Agentic Substrate & Protocol Foundations

## Overview
This document serves as the canonical technical guide for **Phase 1: Agentic Substrate & Protocol Foundations** in `HATH0R-CLI` and the Ray Suite.

Phase 1 delivers four foundational agentic capabilities:
1. **Princeton KV Cache Pre-Warming Engine** (`KVCachePrewarmer` / `hath0r agent prewarm`)
2. **Princeton L2WS Warm-Start Calibration** (`L2WSPredictor` / `hath0r cccd calibrate`)
3. **Structured Hath0r Agent Handoff Protocol (HAHP)** (`HAHPProtocolManager` / `hath0r agent hahp`)
4. **Multi-Agent Directed Acyclic Graph (DAG) Execution & Dependency Runner** (`AgentDAGRunner` / `hath0r agent dag`)

---

## Strategy & Architecture
- **Zero-Token Prefill Warming**: Shared system prompts and OneDrive knowledge context are pre-warmed via zero-token ping anchors prior to subagent fan-out, reducing concurrent prefill spikes by >= 40%.
- **Learning to Warm-Start (L2WS)**: Historical parameter vectors and loss residuals are stored in Redis (`SESSION`) and DynamoDB (`DATA`), allowing CCCD calibration loops to warm-start optimization iterations and accelerate convergence.
- **HAHP Envelope Serialization**: Inter-agent context handoffs serialize working memory scratchpads, state variables, and tool outputs into validated JSON envelopes.
- **DAG Execution & Fan-in Barriers**: `AgentDAGRunner` parses multi-agent graph specs, executes parallel fan-out branches, and synchronizes barrier join nodes.

---

## Command Reference

### `hath0r agent prewarm`
Executes synthetic KV cache pre-warming ping on shared system prompts.
```bash
hath0r agent prewarm --prompt "Canonical System Context"
```

### `hath0r agent dag`
Executes multi-agent DAG workflow dependency specs.
```bash
hath0r agent dag --demo
hath0r agent dag --spec workflow.json
```

### `hath0r agent hahp`
Creates, serializes, and verifies HAHP inter-agent handoff envelopes.
```bash
hath0r agent hahp --sender planner --recipient executor --scratchpad "State updated."
```

### `hath0r agent status`
Displays combined telemetry metrics for KV prewarmer, HAHP, and DAG execution.
```bash
hath0r agent status
```

---

## Verification & Testing
Run unit and integration tests:
```bash
pytest tests/test_phase1_agent.py
```
