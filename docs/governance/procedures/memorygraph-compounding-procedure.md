# MemoryGraph Compounding & Micro Memory Session Standard Operating Procedure

> **Rule Binding**: `CR-MEMORY-COMPOUND-001`  
> **CLI Entrypoint**: `hath0r memory` · `hath0r memory session`

## 1. Purpose

Defines the mandatory step-by-step procedure for initializing `.hath0r/memory/`, reading and writing a true Micro Memory Session (`.hath0r/memory/sessions/`) on every session, compounding task knowledge into `.hath0r/memory/graph.json`, synchronizing `.hath0r/agentgraph/snapshot.json`, and verifying the pre-announcement gate before declaring any task complete.

## 2. Procedure Steps

### Step 1: Start & Read Micro Memory Session at Session Start
At the start of every session, orientation (`hath0r orient`), or task (`hath0r task start`), read the micro-session capsule (which automatically initializes `.hath0r/memory/sessions/current.json` from `latest.json` and top `graph.json` nodes if needed):
```bash
hath0r memory session start --focus "Working on issue #289 micro memory sessions"
hath0r memory session read
```

### Step 2: Write Incremental Micro-Memory Entries During the Session
As observations, decisions, tool findings, or milestones occur during the session, write compact micro-entries to `.hath0r/memory/sessions/current.json`:
```bash
hath0r memory session write "Verified MicroMemorySession <2KB budget and PRECEDES lineage" \
  --kind decision \
  --tag memorygraph \
  --next-step "Run pytest and verify gate"
```

### Step 3: Compound Durable Knowledge with Tracked Source File Hashes
Before calling `hath0r task finish` or announcing task completion to the operator, record the task's durable architectural decisions, root-cause fixes, or episodic outcomes into `.hath0r/memory/graph.json` (optionally binding `--source-file` paths so their SHA-256 digests are tracked in `.hath0r/memory/hashes.json`):
```bash
hath0r memory compound \
  --label "Short descriptive title of learning or decision" \
  --content "Detailed summary of what was built, fixed, or decided and why." \
  --type episode \
  --tags "memorygraph,session,cli" \
  --source-file "src/hath0r_engine/memory/memory_graph.py" \
  --relates-to "concept:tri-graph" \
  --relation DERIVES_FROM
```

### Step 4: Flush Micro Session, Sync File Hashes & Verify Pre-Announcement Memory Gate
Flush/end the micro-session, verify/sync cryptographic file hashes, and run the deterministic gate verification check:
```bash
hath0r memory session end --summary "Completed micro memory session implementation and verification"
hath0r memory hash --check
hath0r memory verify
```
Confirm that:
- `.hath0r/memory/graph.json` is valid and has $\ge 1$ compounded node.
- `.hath0r/memory/sessions/current.json` (or `latest.json`) has `read_count >= 1` and `write_count >= 1`.
- `.hath0r/memory/hashes.json` confirms all `.hath0r/memory/*` files and referenced `source_files` match their on-disk SHA-256 digests (`hashes_verified: True`, `conflicts: 0`).
- `.hath0r/agentgraph/snapshot.json` is synchronized with the `memory` plane.

### Step 5: Execute End-of-Task / Announce Complete
Proceed with `hath0r task finish` or `TaskAnnouncerBot.announce_complete()`, which enforces `verify_compounded()` (graph compounding, session read/write, and SHA-256 hash freshness) prior to announcing completion.

