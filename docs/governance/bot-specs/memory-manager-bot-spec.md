# Bot Specification: `MemoryManagerBot` (`memory-manager-bot`)

> **Bot ID**: `memory-manager-bot`  
> **Class**: `hath0r_cli.bots.memory_manager.MemoryManagerBot`  
> **Engine Backing**: `hath0r_engine.memory.MemoryGraph`, `hath0r_engine.memory.MicroMemorySession`, `hath0r_engine.memory.ReflectionEngine`  
> **Rule Binding**: `CR-MEMORY-COMPOUND-001`, `CR-AGENTGRAPH-001`

## 1. Role & Responsibilities

`MemoryManagerBot` manages the canonical Local Memory Space (`.hath0r/memory/`), dedicated Micro Memory Sessions (`.hath0r/memory/sessions/`), and semantic/episodic `MemoryGraph` (`.hath0r/memory/graph.json`) across all Hath0r repositories. It enforces universal repository presence of `.hath0r/memory/graph.json` and `.hath0r/memory/sessions/current.json`, manages session-level micro-reads and micro-writes (<2KB capsule), compounds task learnings into connected graph nodes and edges (`PRECEDES`, `DERIVES_FROM`), executes autonomous reflection synthesis, synchronizes the `memory` plane of `AgentGraph`, and enforces the pre-announcement completion gate (`read_count >= 1`, `write_count >= 1`, and `compounded_nodes_count >= 1`).

## 2. Capabilities & Actions

| Action | Method | Description |
|--------|--------|-------------|
| `init` / `initialize-memory` | `initialize_memory(dry_run=False)` | Provisions `.hath0r/memory/core_rules.md`, `architecture.md`, `graph.json`, and `.hath0r/memory/sessions/current.json` & `latest.json`. |
| `session-start` | `session_start(focus=None, session_id=None, top_k=5)` | Starts a new micro-session in `.hath0r/memory/sessions/current.json`, recalls prior `latest.json` and top `graph.json` nodes (`read_count >= 1`), and links via `PRECEDES` edge. |
| `session-read` | `session_read(focus=None, top_k=5)` | Reads the active micro-session capsule (<2KB) from `.hath0r/memory/sessions/current.json` (auto-starting if absent) and increments `read_count`. |
| `session-write` | `session_write(summary, kind="observation", tags=None, focus=None, next_steps=None, node_id=None)` | Appends a compact micro-entry to `.hath0r/memory/sessions/current.json`, increments `write_count`, enforces <2KB capsule bound, and syncs session node to `graph.json`. |
| `session-end` | `session_end(summary=None, next_steps=None)` | Flushes `current.json` to `<session-id>.json` and `latest.json`, updates `session:<session_id>` and `PRECEDES`/`DERIVES_FROM` edges in `graph.json`, and syncs `AgentGraph`. |
| `session-status` | `session_status()` | Returns current micro-session read/write counters, byte size, recalled nodes, and gate verification status. |
| `read` / `read-memory` | `read_memory(topic)` | Reads a markdown topic file from `.hath0r/memory/<topic>.md`. |
| `update` / `update-memory` | `update_memory(topic, content, dry_run=False)` | Writes a markdown topic file and upserts a corresponding `topic:<topic>` node in `.hath0r/memory/graph.json`. |
| `search` / `search-memory` | `search_memory(query, node_type, tag, depth, relation)` | Searches `.hath0r/memory/graph.json` and traverses semantic relations up to `depth`. |
| `compound` / `add-node` | `compound_memory(...)` | Adds/updates a structured `MemoryNode` and relational `MemoryEdge`s in `.hath0r/memory/graph.json`, records a micro-session write, runs `ReflectionEngine` consolidation, and syncs `.hath0r/agentgraph/snapshot.json`. |
| `reflect` / `consolidate` | `reflect_memory(dry_run=False)` | Runs sleep-cycle consolidation across episodic/decision clusters to synthesize `insight` nodes. |
| `verify` / `verify-gate` | `verify_compounded(require_compounded=True, require_session=True)` | Verifies `.hath0r/memory/graph.json` contains compounded task knowledge AND `.hath0r/memory/sessions/` has `read_count >= 1` and `write_count >= 1`. |
| `ensure-all` | `ensure_all_repos(root_dir, dry_run=False)` | Discovers all git repositories under `root_dir`, ensures `.hath0r/memory/graph.json` and `.hath0r/memory/sessions/` are initialized and synced with AgentGraph. |
