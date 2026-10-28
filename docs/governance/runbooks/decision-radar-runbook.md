# Runbook: Hath0r Cruise Control Operations

> Canonical Runbook · ID: `RUNBOOK-DECISION-RADAR-001`  
> Epic: #499 / #508 · Tasks: #500–#506

---

## 1. Quick Command Reference

```bash
# Launch Cruise Control Web Radar UI in a split-window browser display (http://127.0.0.1:38090/radar)
hath0r cruise radar --port 38090 --split-window --split-side right

# Seed the canonical 16-node Cruise Control reference topology and render TUI
hath0r cruise tui --seed-demo

# Queue a new decision from an agent (automatically opens/focuses split-window Cruise Control)
hath0r cruise ask \
  --question "Patch and reboot the Parts-API widget VMs" \
  --category "only_you_can_do_this" \
  --agent "@a11152" \
  --unblocks "vm-node-1,vm-node-2" \
  --split-window
```

# Block agent terminal until answered or settled by fact
hath0r decision wait \
  --question "Catalog read-only tools at zero credit balance" \
  --category "only_you_can_do_this" \
  --agent "@a11062" \
  --unblocks "catalog-sync,mcp-ro-gate,billing-guard" \
  --timeout 1.0

# List open decisions ranked by U(d)
hath0r decision list

# Answer a decision
hath0r decision answer <decision-id> --response "Approved"

# Bind a decision to a fact predicate instead of a timer
hath0r decision snooze <decision-id> --fact "file.exists:VERSION"

# Assert a fact and trigger auto-settlement
hath0r decision assert-fact "ci.workflow.passed:sonar-gate"

# Run fact settlement pass
hath0r decision settle
```

---

## 2. REST & SSE Endpoints (`HathorDecisionRadarServer`)

| Method | Path | Description |
|---|---|---|
| `GET` | `/radar` | Cruise Control Radial Sunburst HTML/SVG/Tailwind UI |
| `GET` | `/api/decisions` | Full radar polar snapshot JSON |
| `GET` | `/api/decisions/stream` | Server-Sent Events (SSE) real-time radar stream |
| `POST` | `/api/decisions/request` | Enqueue a new agent decision |
| `POST` | `/api/decisions/answer` | Resolve a decision with operator answer |
| `POST` | `/api/decisions/reject` | Reject a decision |
| `POST` | `/api/decisions/snooze` | Bind a decision to a declarative fact predicate |
| `POST` | `/api/decisions/split-window` | Tile Cruise Control in a right/left split-screen browser window |
| `POST` | `/api/decisions/assert-fact` | Assert a fact and auto-settle matching decisions |
| `POST` | `/api/decisions/settle` | Evaluate all pending fact predicates |
| `POST` | `/api/decisions/seed` | Seed reference topology |
