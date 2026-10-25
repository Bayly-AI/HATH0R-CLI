# CR-MEMORY-COMPOUND-001: Mandatory `.hath0r/memory` Repository Presence, Micro Memory Sessions & Pre-Announcement MemoryGraph Compounding (CRITICAL — org-wide)

> **Status**: Active · **Tier**: Org Invariant (`RulePriority.ORG_INVARIANT`)  
> **Scope**: All repositories across `/Users/raybayly/Development` (`OpenSource`, `1-Nation`, `BAI`, `Ray`, `Websites`)  
> **Enforced by**: `hath0r memory`, `MemoryManagerBot`, `OrientBot`, `TaskAnnouncerBot`, `EndOfTaskBot`, `CleanReposWorkflowBot`, `AgentGraphBot`

---

## 1. Universal `.hath0r/memory`, `.hath0r/memory/sessions`, `.hath0r/memory/hashes.json` & Un-Ignored Graph Folders Invariant

1. Every active project repository in `/Users/raybayly/Development` **MUST** maintain an initialized `.hath0r/memory/` directory containing:
   - `.hath0r/memory/graph.json`: The canonical serialized `MemoryGraph` (`schema_version: "1.0.0"`), storing typed semantic, episodic, and session nodes (`rule`, `concept`, `decision`, `fact`, `episode`, `topic`, `insight`, `session`), relational edges (`ENFORCES`, `REQUIRES`, `DERIVES_FROM`, `SUPERSEDES`, `RELATES_TO`, `RESOLVES`, `PRECEDES`), monotonic `revision` counter, and canonical `content_hash` (`sha256:<64-hex>`).
   - `.hath0r/memory/sessions/`: The dedicated **Micro Memory Session** store containing:
     - `current.json`: Active compact (<2KB) micro-session state (`session_id`, `prior_session_id`, `read_count`, `write_count`, `revision`, `content_hash`, `base_graph_hash`, `active_focus`, `recalled_nodes`, `micro_entries`, `next_steps`).
     - `latest.json`: Most recent completed or active micro-session snapshot for zero-latency cross-session continuity.
     - `<session-id>.json`: Immutable historical micro-session snapshots linked via `PRECEDES` edges in `.hath0r/memory/graph.json`.
   - `.hath0r/memory/hashes.json`: The cryptographic **File Hash & Integrity Manifest** (`schema_version: "hath0r.memory_hashes/1"`), recording SHA-256 digests (`sha256:...`), byte sizes, and monotonic revisions for every file in `.hath0r/memory/` (`graph.json`, `core_rules.md`, `architecture.md`, `sessions/current.json`, `sessions/latest.json`) plus all repository `source_files` referenced by `MemoryGraph` nodes.
   - `.hath0r/memory/core_rules.md`: Canonical local rule summary.
   - `.hath0r/memory/architecture.md`: Repository architectural orientation summary.
2. **Graph Folders MUST NEVER Be Git-Ignored**:
   - Every repository's `.gitignore` **MUST** ensure that all cognitive graph folders are tracked in version control and **NEVER** ignored by Git:
     - `.hath0r/memory/` and `.hath0r/memory/sessions/` (`MemoryGraph`, micro sessions, and `hashes.json`)
     - `.hath0r/agentgraph/` (`AgentGraph` unified `snapshot.json`)
     - `.hath0r/graphs/` (Auxiliary graph definitions)
     - `.hath0r/state/cache/` (`KnowledgeGraph` compiled `knowledge.json`)
     - `.hath0r/state/context/` (`ContextGraph` `session_init.json`)
     - `lib/graph/`, `lib/context/`, `lib/memory/` (Engine graph library directories where present)
   - Broad ignore rules such as `.hath0r/`, `.hath0r/state/`, or unnegated `.hath0r/*.json` are automatically sanitized and accompanied by explicit `!` un-ignore directives (`!.hath0r/memory/**`, `!.hath0r/agentgraph/**`, `!.hath0r/graphs/**`, `!.hath0r/state/cache/**`, `!.hath0r/state/context/**`) by `MemoryManagerBot` and `RepoLayoutBot`.
3. During repository onboarding (`hath0r init`), orientation (`hath0r orient`), task startup (`hath0r task start`), or repository hygiene (`hath0r repo clean` / `clean-repos`), `MemoryManagerBot` **MUST** verify and initialize `.hath0r/memory/graph.json`, `.hath0r/memory/sessions/current.json`, `.hath0r/memory/hashes.json`, and `.gitignore` graph un-ignore rules.
4. Suite-wide compliance is audited and enforced via `hath0r memory ensure-all`, `hath0r memory hash --check`, and `hath0r memory verify` (which verifies `graphs_not_ignored: True` via `git check-ignore`).

---

## 2. Mandatory Micro Memory Session Read & Write on Every Session

1. **Every Session MUST Read and Write a True Micro Memory Session**:
   - **Session Start / Read (`hath0r memory session start` / `hath0r memory session read`)**: At the beginning of every session (`hath0r orient`, `hath0r task start`, or explicit `hath0r memory session read`), the agent/bot **MUST** read the prior micro-session (`latest.json`) and top-ranked active nodes from `graph.json` into `.hath0r/memory/sessions/current.json`, recording `base_graph_hash`, incrementing `read_count >= 1`, and linking the new session node (`session:<session_id>`) to `prior_session_id` via a `PRECEDES` edge.
   - **In-Session Micro-Writes (`hath0r memory session write`)**: During task execution, orientation, knowledge compounding, or cleanup, the agent/bot **MUST** write compact micro-memory entries (`observation`, `decision`, `tool`, `hypothesis`, `blocker`, `milestone`) into `.hath0r/memory/sessions/current.json`, incrementing `write_count >= 1` and `revision` while keeping the micro-capsule strictly bounded (<2KB) for zero-prompt-tax retrieval.
   - **Session End / Flush (`hath0r memory session end`)**: Upon task completion (`hath0r task finish`, `clean-repos`, or `hath0r memory session end`), the micro-session is flushed to `.hath0r/memory/sessions/<session-id>.json` and `.hath0r/memory/sessions/latest.json`, synced into `.hath0r/memory/graph.json` with `PRECEDES` and `DERIVES_FROM` edges, and hashed into `.hath0r/memory/hashes.json`.

---

## 3. Cryptographic SHA-256 File Hashing, Staleness Detection & Optimistic Concurrency (CAS + Auto-Merge)

1. **Cryptographic File Hashing (`hath0r memory hash`)**:
   - Every file in `.hath0r/memory/` and every repository source file referenced in `node.metadata.source_files` is hashed using canonical `SHA-256` (`sha256:<hex>`).
   - If a referenced repository source file is modified on disk such that its current SHA-256 differs from the digest recorded on a `MemoryNode`, `hath0r memory hash --check` and `hath0r memory verify` detect the staleness and either refresh the digest (`hath0r memory hash --sync`) or flag the stale node for update.
2. **Optimistic Concurrency Control (CAS) & Deterministic Auto-Merge**:
   - Every read operation records the last-read `content_hash` and `revision`.
   - Before writing to `graph.json` or `sessions/current.json`, the writer compares the on-disk file's current SHA-256 digest against the expected hash:
     - **Non-Conflicting Concurrent Writes**: If another session or subagent concurrently added distinct nodes, edges, or micro-entries, `MemoryManagerBot` performs a deterministic **set-union auto-merge** of nodes, edges, and micro-entries, increments `revision`, recomputes `content_hash`, and writes atomically via a temporary file + `os.replace`.
     - **True Same-ID / Explicit CAS Conflict (`HASH_CONFLICT`)**: If an explicit `--expected-hash` fails to match the on-disk digest, or if the same node ID was concurrently mutated with incompatible content, the write is rejected with `HASH_CONFLICT` to guarantee zero silent data loss or overwrite conflicts.

---

## 4. Mandatory Pre-Announcement Knowledge Compounding, Session & Hash Gate

1. **No Task Completion Without Memory Compounding + Session Read/Write + Up-to-Date File Hashes**: Every task, bugfix, feature, refactor, research cycle, or repository cleanup **MUST**:
   - Have an active/flushed micro-session with `read_count >= 1` and `write_count >= 1`.
   - Record at least one structured knowledge node (`episode`, `decision`, `fact`, `insight`, `concept`, or `rule`) into `.hath0r/memory/graph.json` **prior to announcing task completion**.
   - Have a synchronized, conflict-free `.hath0r/memory/hashes.json` manifest where all `.hath0r/memory/` files and tracked `source_files` match their current on-disk SHA-256 digests (`hashes_verified: True`).
2. **Hard Gate in `TaskAnnouncerBot`**:
   - `TaskAnnouncerBot.announce_complete()` enforces a deterministic pre-announcement gate via `MemoryManagerBot.verify_compounded()`.
   - If `.hath0r/memory/graph.json` is missing, contains no compounded knowledge node, the micro memory session has not recorded both a read (`read_count >= 1`) and a write (`write_count >= 1`), or `.hath0r/memory/hashes.json` reports stale/conflicting file hashes, `announce_complete` **BLOCKS** completion announcement.

---

## 5. Immediate AgentGraph Synchronization & Reflection Consolidation

1. Whenever `MemoryManagerBot` compounds knowledge or flushes a micro-session into `.hath0r/memory/graph.json`:
   - It **MUST** automatically trigger `ReflectionEngine.consolidate_sleep_cycle()` when tag clusters reach the synthesis threshold ($\ge 2$ related episodes/decisions), generating higher-order `insight` nodes linked via `DERIVES_FROM` edges.
   - It **MUST** immediately update `.hath0r/memory/hashes.json` and synchronize `.hath0r/agentgraph/snapshot.json` via `AgentGraphBot.sync(persist=True)` so that `hath0r agentgraph query` and `hath0r memory search` reflect the newly compounded memory and session lineage with zero lag.

