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
| `POST` | `/api/decisions/update` | Upsert or update a decision (stateless agent update, #520) |
| `POST` | `/api/decisions/dep` | Register a task dependency edge (#532) |

---

## 3. Keeping the Radar in Sync with the CLI (#532)

Each CLI command writes to the decision store of the folder it runs in (`<cwd>/.hath0r/decisions/`) and forwards the change to the server on `HATH0R_CRUISE_PORT` (default `38090`). That server is usually the `Hath0r-Cruise-Control` container, which keeps its own store.

```bash
# Is the server reachable, current, and serving which store?
hath0r cruise status

# Push every open decision and dependency edge in this folder's store to the running server
hath0r cruise sync [--port 38090]
```

`cruise ask` / `cruise update` / `cruise dep` print a warning when forwarding fails, instead of failing silently.

### Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `cruise status` shows `stale: true`, or sync warns `404` | The container image predates the API the CLI uses | Rebuild: `docker compose -f hath0r-atc/deploy/docker/docker-compose.yml up -d --build cruise-control`, then `hath0r cruise sync` |
| Radar shows the `@p4010`-style reference topology | The server was started with `--seed-demo`, which wipes its store on every start | Remove `--seed-demo` from the service command; seed on demand with `POST /api/decisions/seed` |
| `cruise radar --detached` returns but nothing listens | Spawned child failed to start | `hath0r cruise status`; run `hath0r cruise radar --foreground` to see the error |

