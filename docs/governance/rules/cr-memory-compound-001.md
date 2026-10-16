# CR-MEMORY-COMPOUND-001: Mandatory `.hath0r/memory` Repository Presence & Pre-Announcement MemoryGraph Compounding (CRITICAL — org-wide)

> **Status**: Active · **Tier**: Org Invariant (`RulePriority.ORG_INVARIANT`)  
> **Scope**: All repositories across `/Users/raybayly/Development` (`OpenSource`, `1-Nation`, `BAI`, `Ray`, `Websites`)  
> **Enforced by**: `hath0r memory`, `MemoryManagerBot`, `TaskAnnouncerBot`, `EndOfTaskBot`, `CleanReposWorkflowBot`, `AgentGraphBot`

---

## 1. Universal `.hath0r/memory` Repository Invariant

1. Every active project repository in `/Users/raybayly/Development` **MUST** maintain an initialized `.hath0r/memory/` directory containing:
   - `.hath0r/memory/graph.json`: The canonical serialized `MemoryGraph` (`schema_version: "1.0.0"`), storing typed semantic and episodic nodes (`rule`, `concept`, `decision`, `fact`, `episode`, `topic`, `insight`) and relational edges (`ENFORCES`, `REQUIRES`, `DERIVES_FROM`, `SUPERSEDES`, `RELATES_TO`, `RESOLVES`, `PRECEDES`).
   - `.hath0r/memory/core_rules.md`: Canonical local rule summary.
   - `.hath0r/memory/architecture.md`: Repository architectural orientation summary.
2. During repository onboarding (`hath0r init`), orientation (`hath0r orient`), or repository hygiene (`hath0r repo clean` / `clean-repos`), `MemoryManagerBot.ensure_memory_space()` **MUST** verify and initialize `.hath0r/memory/graph.json` if missing.
3. Suite-wide compliance is audited and enforced via `hath0r memory ensure-all`.

---

## 2. Mandatory Pre-Announcement Knowledge Compounding

1. **No Task Completion Without Memory Compounding**: Every task, bugfix, feature, refactor, research cycle, or repository cleanup **MUST** record at least one structured knowledge node (`episode`, `decision`, `fact`, `insight`, `concept`, or `rule`) into `.hath0r/memory/graph.json` **prior to announcing task completion**.
2. **Explicit + Automated Dual Compounding**:
   - **Explicit Agent Compounding**: Agents completing a task MUST run `hath0r memory compound` (or `hath0r memory add`) to record key architectural decisions, root-cause fixes, or episodic learnings with relational edges (`RESOLVES`, `DERIVES_FROM`, `RELATES_TO`, `SUPERSEDES`).
   - **Automated Workflow Compounding**: `end-of-task-factory.yaml` (`hath0r task finish`), `EndOfTaskBot`, and `CleanReposWorkflowBot` (Step 6) automatically invoke `MemoryManagerBot.compound_memory()` to capture task/PR/cleanup context into `.hath0r/memory/graph.json`.
3. **Hard Gate in `TaskAnnouncerBot`**:
   - `TaskAnnouncerBot.announce_complete()` enforces a deterministic pre-announcement gate via `MemoryManagerBot.verify_compounded()`.
   - If `.hath0r/memory/graph.json` is missing or contains no compounded knowledge node (beyond static bootstrap seeds), `announce_complete` **BLOCKS** completion announcement until knowledge is compounded.

---

## 3. Immediate AgentGraph Synchronization & Reflection Consolidation

1. Whenever `MemoryManagerBot.compound_memory()` adds or updates nodes/edges in `.hath0r/memory/graph.json`:
   - It **MUST** automatically trigger `ReflectionEngine.consolidate_sleep_cycle()` when tag clusters reach the synthesis threshold ($\ge 2$ related episodes/decisions), generating higher-order `insight` nodes linked via `DERIVES_FROM` edges.
   - It **MUST** immediately synchronize `.hath0r/agentgraph/snapshot.json` via `AgentGraphBot.sync(persist=True)` so that `hath0r agentgraph query` and `hath0r memory search` reflect the newly compounded memory with zero lag.
