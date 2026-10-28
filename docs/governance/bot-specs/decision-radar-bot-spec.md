# Bot Specification: DecisionRadarBot

> Canonical Bot Specification · Hath0r Agentic Framework  
> Updated: 2026-10-28 · Epic: #499 · Issues: #500–#506

---

## 1. Role & Identity

- **Bot Name**: `decision-radar-bot`
- **Class Name**: `DecisionRadarBot`
- **Companion Engines**: `DecisionGraph`, `FactSettlementEngine`, `WorkBoundaryGate`
- **Subsystem**: `HATH0R-CLI` (`src/hath0r_cli/bots/decision_radar_bot.py`)
- **CLI Command**: `hath0r decision` / `hath0r radar`
- **Contract Schema**: `contracts/hath0r-decision-spec-v1.schema.json`
- **Primary Function**: Cybernetic control layer between 10–30 concurrent AI coding agents and the human operator. Models work dependencies as a DAG, ranks decisions by transitive downstream work unblocked $U(d)$, replaces timer snoozing with event-driven fact settlement, enforces HMAC-signed input/output work boundary gates, and drives the Minority Report Radial Sunburst UI.

---

## 2. Supported Conversational & CLI Intents

1. `"hath0r decision radar"` / `"hath0r radar"`
2. `"hath0r decision tui"`
3. `"hath0r decision wait"`
4. `"hath0r decision ask"`
5. `"hath0r decision list"`
6. `"hath0r decision answer"`
7. `"hath0r decision snooze"`
8. `"hath0r decision settle"`
9. `"hath0r decision approve-in"` / `"hath0r decision approve-out"`

---

## 3. State Persistence & MemoryGraph Integration

- **Active Queue Store**: `.hath0r/decisions/active.json` (protected by optimistic Compare-And-Swap `content_hash` and atomic `os.replace`).
- **Archive Store**: `.hath0r/decisions/archive.json`.
- **Fact Ledger**: `.hath0r/decisions/facts.json`.
- **Boundary Handshake Ledger**: `.hath0r/decisions/ledger.json`.
- **MemoryGraph Compounding**: Every answered or event-settled decision compounds a `decision:<id>` node with `RESOLVES` edges into `.hath0r/memory/graph.json` via `MemoryManagerBot.compound_memory`.
