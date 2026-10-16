# CR-MEMORY-COMPOUND-001: Mandatory `.hath0r/memory` Repository Presence, Micro Memory Sessions & Pre-Announcement MemoryGraph Compounding (CRITICAL — org-wide)

> **Status**: Active · **Tier**: Org Invariant (`RulePriority.ORG_INVARIANT`)  
> **Scope**: All repositories across `/Users/raybayly/Development` (`OpenSource`, `1-Nation`, `BAI`, `Ray`, `Websites`)  
> **Enforced by**: `hath0r memory`, `MemoryManagerBot`, `OrientBot`, `TaskAnnouncerBot`, `EndOfTaskBot`, `CleanReposWorkflowBot`, `AgentGraphBot`

---

## 1. Universal `.hath0r/memory` & `.hath0r/memory/sessions` Repository Invariant

1. Every active project repository in `/Users/raybayly/Development` **MUST** maintain an initialized `.hath0r/memory/` directory containing:
   - `.hath0r/memory/graph.json`: The canonical serialized `MemoryGraph` (`schema_version: "1.0.0"`), storing typed semantic, episodic, and session nodes (`rule`, `concept`, `decision`, `fact`, `episode`, `topic`, `insight`, `session`) and relational edges (`ENFORCES`, `REQUIRES`, `DERIVES_FROM`, `SUPERSEDES`, `RELATES_TO`, `RESOLVES`, `PRECEDES`).
   - `.hath0r/memory/sessions/`: The dedicated **Micro Memory Session** store containing:
     - `current.json`: Active compact (<2KB) micro-session state (`session_id`, `prior_session_id`, `read_count`, `write_count`, `active_focus`, `recalled_nodes`, `micro_entries`, `next_steps`).
     - `latest.json`: Most recent completed or active micro-session snapshot for zero-latency cross-session continuity.
     - `<session-id>.json`: Immutable historical micro-session snapshots linked via `PRECEDES` edges in `.hath0r/memory/graph.json`.
   - `.hath0r/memory/core_rules.md`: Canonical local rule summary.
   - `.hath0r/memory/architecture.md`: Repository architectural orientation summary.
2. During repository onboarding (`hath0r init`), orientation (`hath0r orient`), task startup (`hath0r task start`), or repository hygiene (`hath0r repo clean` / `clean-repos`), `MemoryManagerBot` **MUST** verify and initialize `.hath0r/memory/graph.json` and `.hath0r/memory/sessions/current.json`.
3. Suite-wide compliance is audited and enforced via `hath0r memory ensure-all`.

---

## 2. Mandatory Micro Memory Session Read & Write on Every Session

1. **Every Session MUST Read and Write a True Micro Memory Session**:
   - **Session Start / Read (`hath0r memory session start` / `hath0r memory session read`)**: At the beginning of every session (`hath0r orient`, `hath0r task start`, or explicit `hath0r memory session read`), the agent/bot **MUST** read the prior micro-session (`latest.json`) and top-ranked active nodes from `graph.json` into `.hath0r/memory/sessions/current.json`, incrementing `read_count >= 1` and linking the new session node (`session:<session_id>`) to `prior_session_id` via a `PRECEDES` edge.
   - **In-Session Micro-Writes (`hath0r memory session write`)**: During task execution, orientation, knowledge compounding, or cleanup, the agent/bot **MUST** write compact micro-memory entries (`observation`, `decision`, `tool`, `hypothesis`, `blocker`, `milestone`) into `.hath0r/memory/sessions/current.json`, incrementing `write_count >= 1` while keeping the micro-capsule strictly bounded (<2KB) for zero-prompt-tax retrieval.
   - **Session End / Flush (`hath0r memory session end`)**: Upon task completion (`hath0r task finish`, `clean-repos`, or `hath0r memory session end`), the micro-session is flushed to `.hath0r/memory/sessions/<session-id>.json` and `.hath0r/memory/sessions/latest.json`, and synced into `.hath0r/memory/graph.json` with `PRECEDES` and `DERIVES_FROM` edges.

---

## 3. Mandatory Pre-Announcement Knowledge Compounding & Session Gate

1. **No Task Completion Without Memory Compounding + Session Read/Write**: Every task, bugfix, feature, refactor, research cycle, or repository cleanup **MUST**:
   - Have an active/flushed micro-session with `read_count >= 1` and `write_count >= 1`.
   - Record at least one structured knowledge node (`episode`, `decision`, `fact`, `insight`, `concept`, or `rule`) into `.hath0r/memory/graph.json` **prior to announcing task completion**.
2. **Explicit + Automated Dual Compounding**:
   - **Explicit Agent Compounding**: Agents run `hath0r memory session read`, `hath0r memory session write`, and `hath0r memory compound` to record session progress and durable architectural decisions/episodic learnings.
   - **Automated Workflow Compounding**: `OrientBot`, `hath0r task start`, `hath0r task finish` (`EndOfTaskBot`), and `CleanReposWorkflowBot` automatically read/write the micro-session and invoke `MemoryManagerBot.compound_memory()`.
3. **Hard Gate in `TaskAnnouncerBot`**:
   - `TaskAnnouncerBot.announce_complete()` enforces a deterministic pre-announcement gate via `MemoryManagerBot.verify_compounded()`.
   - If `.hath0r/memory/graph.json` is missing, contains no compounded knowledge node, or the micro memory session has not recorded both a read (`read_count >= 1`) and a write (`write_count >= 1`), `announce_complete` **BLOCKS** completion announcement.

---

## 4. Immediate AgentGraph Synchronization & Reflection Consolidation

1. Whenever `MemoryManagerBot` compounds knowledge or flushes a micro-session into `.hath0r/memory/graph.json`:
   - It **MUST** automatically trigger `ReflectionEngine.consolidate_sleep_cycle()` when tag clusters reach the synthesis threshold ($\ge 2$ related episodes/decisions), generating higher-order `insight` nodes linked via `DERIVES_FROM` edges.
   - It **MUST** immediately synchronize `.hath0r/agentgraph/snapshot.json` via `AgentGraphBot.sync(persist=True)` so that `hath0r agentgraph query` and `hath0r memory search` reflect the newly compounded memory and session lineage with zero lag.
