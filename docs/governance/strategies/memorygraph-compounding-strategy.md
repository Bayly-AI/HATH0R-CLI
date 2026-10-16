# MemoryGraph Compounding, Micro Memory Sessions & Pre-Announcement Gate Strategy

> **Rule Binding**: `CR-MEMORY-COMPOUND-001` · `CR-AGENTGRAPH-001`  
> **Subsystem**: `hath0r_engine.memory` · `hath0r_cli.bots.memory_manager` · `hath0r_cli.bots.agentgraph_bot`

## 1. Strategic Objective

Autonomous agents lose institutional context across sessions when task learnings remain trapped in ephemeral chat transcripts or unindexed markdown notes. The **MemoryGraph Compounding & Micro Memory Session Strategy** establishes a two-tier memory architecture in every repository:
1. **True Micro Memory Sessions (`.hath0r/memory/sessions/`)**: A compact (<2KB), zero-prompt-tax working memory capsule (`current.json`, `latest.json`, `<session-id>.json`) that is **read at the start of every session** and **written throughout every session**.
2. **Compounding Institutional MemoryGraph (`.hath0r/memory/graph.json`)**: A living, bitemporal semantic network where micro-sessions and task episodes compound into durable architectural insights prior to completion announcement.

## 2. Architectural Pillars

1. **Universal Repository Memory Space (`.hath0r/memory/` & `.hath0r/memory/sessions/`)**:
   - Every repository in `/Users/raybayly/Development` maintains `.hath0r/memory/graph.json`, `.hath0r/memory/sessions/current.json`, `.hath0r/memory/sessions/latest.json`, `.hath0r/memory/core_rules.md`, and `.hath0r/memory/architecture.md`.
   - Repository initialization (`hath0r init`), orientation (`hath0r orient`), task startup (`hath0r task start`), cleanup (`hath0r repo clean`), and suite-wide audits (`hath0r memory ensure-all`) guarantee zero uninitialized repositories.

2. **True Micro Memory Session Read/Write Lifecycle (`hath0r memory session`)**:
   - **Session Read (`start` / `read`)**: Recalls the prior micro-session (`latest.json`) and top-ranked active nodes from `graph.json` into a compact (<2KB) capsule (`current.json`), incrementing `read_count` and linking `session:<session_id>` via a `PRECEDES` edge.
   - **Session Write (`write`)**: Appends bounded micro-entries (`observation`, `decision`, `tool`, `hypothesis`, `blocker`, `milestone`) and updates `active_focus` / `next_steps` during execution, incrementing `write_count` while auto-rolling older micro-entries to preserve the <2KB budget.
   - **Session End (`end`)**: Flushes the micro-session to `<session-id>.json` and `latest.json`, records `session:<session_id>` and `DERIVES_FROM` edges in `graph.json`, and syncs `AgentGraph`.

3. **Dual-Path Knowledge Compounding (Explicit + Automated)**:
   - **Explicit Agent Compounding**: Agents record high-signal architectural decisions (`decision`), episodic task outcomes (`episode`), facts (`fact`), concepts (`concept`), and rules (`rule`) via `hath0r memory compound`.
   - **Automated Lifecycle Compounding**: `OrientBot`, `hath0r task start`, `EndOfTaskBot` (`hath0r task finish`), and `CleanReposWorkflowBot` automatically read/write the micro-session and compound task/PR summaries.

4. **Autonomous Reflection & Insight Consolidation (`ReflectionEngine`)**:
   - As episodic and decision nodes accumulate shared tags ($\ge 2$ nodes per tag cluster), `ReflectionEngine.consolidate_sleep_cycle()` synthesizes higher-order `insight` nodes linked via `DERIVES_FROM` edges.

5. **Hard Pre-Announcement Gate (`TaskAnnouncerBot`)**:
   - `TaskAnnouncerBot.announce_complete()` verifies via `MemoryManagerBot.verify_compounded()` that:
     1. `.hath0r/memory/graph.json` exists and contains compounded task knowledge, AND
     2. `.hath0r/memory/sessions/current.json` (or `latest.json`) has recorded both a session read (`read_count >= 1`) and a session write (`write_count >= 1`).
