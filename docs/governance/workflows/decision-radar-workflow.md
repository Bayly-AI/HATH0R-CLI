# Workflow: Hath0r Cruise Control Lifecycle

> Canonical Workflow · ID: `WORKFLOW-DECISION-RADAR-001`  
> Config: `cfg/workflows/decision-radar-workflow.yaml` · Epic: #499 / #508

---

## 1. End-to-End Decision & Settlement Flow

```mermaid
flowchart TD
    InGate["1. Input Boundary Gate\n(Start or hold work)"] --> Exec["2. Agent Execution across\n10-30 Concurrent Terminals"]
    Exec --> Blocked["3. Agent Hits Decision Point\n(hath0r cruise wait)"]
    Blocked --> Graph["4. DecisionGraph Computes\nTransitive Unblock Score U(d)"]
    Graph --> Radar["5. Cruise Control Radial UI\n7 Canonical Wedges"]
    Radar -->|Human Answers| Resolve["6a. RESOLVED_HUMAN\nHMAC Sign + Unblock"]
    Radar -->|Snooze on Fact| FactWait["6b. WAITING_FACT\nBind Predicate (Not Timer)"]
    FactWait -->|Probe Satisfied| AutoSettle["6c. SETTLED_BY_EVENT\nZero-Touch Auto-Settle"]
    Resolve --> OutGate["7. Output Boundary Gate\n(Accept delivered work)"]
    AutoSettle --> OutGate
    OutGate --> Compound["8. MemoryGraph CAS Compounding\n(.hath0r/memory/graph.json)"]
```

---

## 2. Stage Specifications

1. **Stage 1 (`input_boundary_gate`)**: Validates prompt scope, token budget cap, and permitted tools before agent execution begins.
2. **Stage 2 (`impact_reranking`)**: Evaluates transitive reachability in `DecisionGraph` and orders all waiting questions descending by $U(d)$.
3. **Stage 3 (`fact_settlement_loop`)**: Evaluates `file.exists`, `memory.fact.asserted`, `agent.task.completed`, `git.pr.merged`, `ci.workflow.passed`, and `endpoint.health.ok` predicates.
4. **Stage 4 (`output_boundary_gate`)**: Signs off unified code diffs and test artifacts with HMAC-SHA256 tokens and compounds `decision:<id>` nodes into `.hath0r/memory/graph.json`.
