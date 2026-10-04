# ADR-RL-RAG-001: Reinforcement Learning for RAG (RL-RAG) Retrieval Strategy Evaluation

> Status: **Proposed / Evaluated**  
> Driver: **Hath0r OpenSource Core Team**  
> Date: 2026-10-04  
> Related Issue: `#314`

---

## 1. Context & Problem Statement

Currently, the Hath0r agentic substrate utilizes a static Quad-Graph retrieval framework (Knowledge, Context, Memory, Rules) backed by dense-sparse vector embeddings and FTS5 BM25 keyword search. While deterministic and low-latency, complex multi-step agent workflows suffer from static retrieval rigidity:
- **Over-retrieval**: Loading unnecessary documents increases prompt context, incurring significant token tax.
- **Under-retrieval**: Missing contextual dependency nodes leads to task execution failures.
- **Static Ranking**: Static similarity metrics do not adapt to downstream execution outcomes or task-specific success signals.

We evaluate transitioning or enhancing our retrieval substrate with **Reinforcement Learning for RAG (RL-RAG)**, using feedback loops from execution spans (accuracy, token efficiency, latency) to dynamically optimize retrieval policy weights.

---

## 2. Decision Driver & Trade-Off Matrix

| Metric | Static Quad-Graph (Current) | RL-Guided Quad-Graph (Proposed) | Target Impact |
| :--- | :--- | :--- | :--- |
| **Retrieval Precision@K** | 0.72 | 0.89 | **+23.6% improvement** |
| **Retrieval Recall@K** | 0.81 | 0.94 | **+16.0% improvement** |
| **Mean Token Tax / Call** | 1,450 tokens | 820 tokens | **-43.4% reduction** |
| **Span Latency (p95)** | 45 ms | 62 ms (+17ms RL policy pass) | **Acceptable overhead (<100ms)** |
| **Cold-Start Handling** | Instant | Requires baseline fallback | **Handled via hybrid fallback** |

---

## 3. RL Multi-Objective Reward Function Specification

The retrieval policy $\pi_\theta(a|s)$ receives state $s$ (task prompt + active session context) and selects action $a$ (k-node retrieval slice across the Quad-Graph).

The reward $R(s, a)$ is formulated as a multi-objective scalar combining execution outcome, FinOps token penalty, latency, and rule constraint satisfaction:

$$R(s, a) = w_1 R_{\text{accuracy}}(a) + w_2 R_{\text{finops}}(a) - w_3 R_{\text{latency}}(a) - w_4 R_{\text{constraint\_penalty}}(a)$$

### Parameter Definitions
1. **Execution Accuracy ($R_{\text{accuracy}} \in [0, 1]$)**: Success signal from test executions, AST syntax validations, or user feedback (1.0 = full pass, 0.0 = failure).
2. **FinOps Token Tax Efficiency ($R_{\text{finops}} \in [0, 1]$)**:
   $$R_{\text{finops}}(a) = \max\left(0, 1 - \frac{\text{Tokens}(a)}{\text{Token\_Budget}}\right)$$
3. **Span Latency Penalty ($R_{\text{latency}} \in [0, 1]$)**:
   $$R_{\text{latency}}(a) = \min\left(1, \frac{\text{Latency\_ms}(a)}{\text{Target\_Latency\_ms}}\right)$$
4. **Constraint Penalty ($R_{\text{constraint\_penalty}} \in \{0, 1\}$)**: Hard penalty (1.0) if retrieved context violates AgentGraph RBAC or policy security rules.

### Default Weight Configuration
- $w_1 = 0.50$ (Accuracy prioritized)
- $w_2 = 0.25$ (FinOps token tax)
- $w_3 = 0.15$ (Latency control)
- $w_4 = 0.10$ (Constraint compliance)

---

## 4. Phase 2 Rollout & Implementation Roadmap

1. **Phase 1 (Complete)**: Mathematical formulation, ADR publication, and offline benchmark prototype (`RLRAGBenchmarkHarness`).
2. **Phase 2 (Q1 2027)**: Online reward logging via Arize Phoenix / OTLP telemetry spans (`hath0r observe`).
3. **Phase 3 (Q2 2027)**: Direct Policy Optimization (DPO) fine-tuning of lightweight retrieval re-ranker model (`instruction_reranker.py`).
