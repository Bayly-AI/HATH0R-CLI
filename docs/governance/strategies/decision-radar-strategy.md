# Strategy: Hath0r Cruise Control (Agent Decision Control Layer)

> Canonical Governance Strategy · ID: `STRAT-DECISION-RADAR-001`  
> Epic: #499 / #508 · Tasks: #500–#506 · Rule Compliance: `CR-CLI-FEATURE-STANDARD-001`, `CR-MEMORY-COMPOUND-001`

---

## 1. Architectural Rationale

When an operator coordinates 10 to 30 concurrent AI coding agent terminals, the agents are no longer the bottleneck—the human operator's attention is. Without a unified control plane:
- High-leverage root decisions sit buried behind trivial leaf questions.
- Timer-based snoozing ("ask me again in 24 hours") creates stale interruptions even after external events (PR merges, CI runs, sibling completions) have already resolved the blocker.
- Unregulated input scopes waste token budgets, and unreviewed output deliveries risk branch integrity.

The **Hath0r Decision Radar** resolves these bottlenecks through four coupled mechanisms:

1. **Graph-Theoretic Dependency & Transitive Unblocking Reranker (`DecisionGraph`)**:
   Models waiting agents ($\mathcal{A}$), decisions ($\mathcal{D}$), and downstream tasks ($\mathcal{T}$) as a directed acyclic graph (DAG). Ranks every waiting decision by its **Transitive Unblocking Impact Score**:
   $$U(d) = \sum_{t \in \text{TransitiveUnblocked}(d)} w(t) \cdot \kappa(t) + \sum_{a \in \text{BlockedAgents}(d)} \alpha(a)$$
2. **Event-Driven Fact Settlement Engine (`FactSettlementEngine`)**:
   Replaces arbitrary countdown timers with declarative **Fact Predicates** (`git.pr.merged`, `ci.workflow.passed`, `agent.task.completed`, `file.exists`, `memory.fact.asserted`). Satisfied predicates auto-settle waiting questions (`STATUS=SETTLED_BY_EVENT`) without human intervention.
3. **Bidirectional Work Boundary Gates (`WorkBoundaryGate`)**:
   Enforces HMAC-SHA256 signed approvals on what goes into agent work (`INPUT` gate: prompt intent, token cap, tool RBAC) and what comes out (`OUTPUT` gate: code diffs, test proofs, PR drafts).
4. **Cruise Control Radial Sunburst UX (`HathorDecisionRadarServer` / `HathorCruiseControlServer`)**:
   Projects all active decisions onto a concentric circular radar around the operator hub across 7 canonical semantic wedges.

---

## 2. The 7 Canonical Decision Wedges

| Wedge ID | Display Label | Role in Agent Lifecycle |
|---|---|---|
| `needs_card` | **Needs a card** | Financial quotas, cloud credit tiers, paid API provisioning |
| `only_you_can_do_this` | **Only you can do this** | Human-only credentials, master keys, production secrets |
| `approve_message` | **Approve a message** | External communications, PR comments, webhook notices |
| `set_product_rule` | **Set a product rule** | Architecture invariants, schema trade-offs, domain rules |
| `start_hold_work` | **Start or hold work** | Input boundary gate, worker dispatch, budget allocation |
| `accept_delivered_work` | **Accept delivered work** | Output boundary gate, diff review, merge sign-off |
| `keep_ledger_true` | **Keep the ledger true** | Orphaned worker cleanup, state lock reconciliation, MemoryGraph sync |
