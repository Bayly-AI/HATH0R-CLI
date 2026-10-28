# Playbook: Cruise Control Queue Triage & Bottleneck Recovery

> Canonical Playbook · ID: `PLAYBOOK-DECISION-RADAR-001`  
> Epic: #499 · Tasks: #500–#506, #508

---

## 1. Scenario A: Operator Queue Congestion (>20 Open Decisions Across Terminals)

### Symptoms
- 10–30 agent terminals are simultaneously waiting on human input.
- Operator cannot tell which question matters most.

### Resolution Steps
1. Run `hath0r decision settle` first to clear out any questions whose underlying facts (`git.pr.merged`, `file.exists`, `agent.task.completed`, `memory.fact.asserted`) have already been settled by events.
2. Run `hath0r decision list` or open `hath0r decision radar` to view decisions sorted descending by **Transitive Unblocking Impact Score $U(d)$**.
3. Resolve `P0` and `P1` decisions with the highest `|| N` unblock badge first to free the maximum number of downstream workers.

---

## 2. Scenario B: Stalled Fact-Bound Questions

### Symptoms
- A decision remains in `WAITING_FACT` state even though an external deployment or PR completed outside local polling.

### Resolution Steps
1. Assert the verified external fact into the radar fact ledger:
   ```bash
   hath0r decision assert-fact "git.pr.merged:Bayly-AI/HATH0R-CLI#499" --reason "PR merged on GitHub"
   ```
2. Verify automatic settlement (`STATUS=SETTLED_BY_EVENT`) via:
   ```bash
   hath0r decision list --archived
   ```

---

## 3. Scenario C: Orphaned Worker / Ledger Drift ("Keep the Ledger True")

### Symptoms
- An agent worker exited unexpectedly while holding an in-progress task lock (`drv-a0d4c331`).

### Resolution Steps
1. Filter the `keep_ledger_true` wedge:
   ```bash
   hath0r decision list --category keep_ledger_true
   ```
2. Answer or reject the orphaned state entry so downstream worker pools reclaim capacity and compound the resolution into `.hath0r/memory/graph.json`.
