# Bot Specification: `MemoryManagerBot` (`memory-manager-bot`)

> **Bot ID**: `memory-manager-bot`  
> **Class**: `hath0r_cli.bots.memory_manager.MemoryManagerBot`  
> **Engine Backing**: `hath0r_engine.memory.MemoryGraph`, `hath0r_engine.memory.ReflectionEngine`  
> **Rule Binding**: `CR-MEMORY-COMPOUND-001`, `CR-AGENTGRAPH-001`

## 1. Role & Responsibilities

`MemoryManagerBot` manages the canonical Local Memory Space (`.hath0r/memory/`) and semantic/episodic `MemoryGraph` (`.hath0r/memory/graph.json`) across all Hath0r repositories. It enforces universal repository presence of `.hath0r/memory/graph.json`, compounds task learnings into connected graph nodes and edges, executes autonomous reflection synthesis, synchronizes the `memory` plane of `AgentGraph`, and enforces the pre-announcement completion gate.

## 2. Capabilities & Actions

| Action | Method | Description |
|--------|--------|-------------|
| `init` / `initialize-memory` | `initialize_memory(dry_run=False)` | Provisions `.hath0r/memory/core_rules.md`, `architecture.md`, and `graph.json` with canonical seed nodes and edges, plus repository orientation node. |
| `read` / `read-memory` | `read_memory(topic)` | Reads a markdown topic file from `.hath0r/memory/<topic>.md`. |
| `update` / `update-memory` | `update_memory(topic, content, dry_run=False)` | Writes a markdown topic file and upserts a corresponding `topic:<topic>` node in `.hath0r/memory/graph.json`. |
| `search` / `search-memory` | `search_memory(query, node_type, tag, depth, relation)` | Searches `.hath0r/memory/graph.json` and traverses semantic relations up to `depth`. |
| `compound` / `add-node` | `compound_memory(...)` | Adds/updates a structured `MemoryNode` (`episode`, `decision`, `fact`, `insight`, `concept`, `rule`) and relational `MemoryEdge`s in `.hath0r/memory/graph.json`, runs `ReflectionEngine` consolidation, and syncs `.hath0r/agentgraph/snapshot.json`. |
| `reflect` / `consolidate` | `reflect_memory(dry_run=False)` | Runs sleep-cycle consolidation across episodic/decision clusters to synthesize `insight` nodes. |
| `verify` / `verify-gate` | `verify_compounded(require_compounded=True)` | Verifies `.hath0r/memory/graph.json` exists and contains compounded task knowledge beyond static seed nodes. |
| `ensure-all` | `ensure_all_repos(root_dir, dry_run=False)` | Discovers all git repositories under `root_dir`, ensures `.hath0r/memory/graph.json` is initialized and populated with repository knowledge, and syncs AgentGraph. |
