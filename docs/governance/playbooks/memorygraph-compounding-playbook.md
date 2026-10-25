# MemoryGraph Compounding & Micro Memory Session Playbook

> **Rule Binding**: `CR-MEMORY-COMPOUND-001`  
> **Target Audience**: Autonomous Agents, Subagents, and Operators

## 1. When to Use This Playbook

Execute this playbook on **every session and task** (at session start, during execution, and prior to announcing completion), during `clean-repos` (Step 1, Step 6 & Step 13), and whenever onboarding or auditing repositories across `/Users/raybayly/Development`.

## 2. Micro Memory Session Capsule Specification (`.hath0r/memory/sessions/`)

Each repository maintains a dedicated `.hath0r/memory/sessions/` directory containing:
- `current.json`: Active micro-session (<2KB JSON payload)
- `latest.json`: Most recently updated/flushed micro-session
- `<session-id>.json`: Archived session snapshots

| Field | Type | Description |
|-------|------|-------------|
| `session_id` | `str` | Unique session identifier (e.g., `sess-20261016-081000-a1b2c3`) |
| `prior_session_id` | `str \| None` | Previous session ID linked via `PRECEDES` edge in `graph.json` |
| `read_count` | `int` | Number of session reads in this session ($\ge 1$ required by gate) |
| `write_count` | `int` | Number of micro-writes in this session ($\ge 1$ required by gate) |
| `active_focus` | `str` | Concise current objective or task focus |
| `recalled_nodes` | `list[dict]` | Top-ranked compact nodes recalled from `graph.json` at session read |
| `micro_entries` | `list[dict]` | Bounded list of `{timestamp, kind, summary, tags, node_id}` entries |
| `next_steps` | `list[str]` | Hand-off action items for the next session |

## 3. Node Type & Relational Edge Guide (`graph.json`)

| Node Type | When to Use | Default Importance | Example ID Prefix |
|-----------|-------------|--------------------|-------------------|
| `session` | Flushed or active Micro Memory Session capsule | `0.70` | `session:` |
| `episode` | Completed feature, bugfix, or clean-repo task outcome | `0.75` | `episode:` |
| `decision` | Architectural Decision Record (ADR) or design tradeoff | `0.90` | `decision:` |
| `fact` | Verified system invariant, endpoint, or configuration truth | `0.80` | `fact:` |
| `insight` | Synthesized pattern across $\ge 2$ episodes/decisions | `0.85` | `insight:` |
| `concept` | Core domain or substrate abstraction | `0.90` | `concept:` |
| `rule` | Governance policy or operational constraint | `1.00` | `rule:` |

Relational edges: `PRECEDES` (session lineage), `DERIVES_FROM` (session/insight derivation), `ENFORCES`, `RESOLVES`, `SUPERSEDES`, `RELATES_TO`.

## 4. Playbook Execution Recipes

### Recipe A: Session Start Read + In-Session Micro-Write
```bash
# 1. Start or read active micro memory session
hath0r memory session start --focus "Implement micro memory session read/write"
hath0r memory session read

# 2. Write a micro-memory observation or decision during the session
hath0r memory session write "Wired MicroMemorySession into OrientBot and MemoryManagerBot" \
  --kind milestone \
  --tag "memorygraph" \
  --next-step "Verify gate with hath0r memory verify"
```

### Recipe B: Compounding Task Knowledge & Ending Session at Task Completion
```bash
hath0r memory compound \
  --id "episode:issue-289-micro-memory-session" \
  --type episode \
  --label "Enforced True Micro Memory Session Read/Write on Every Session" \
  --content "Added .hath0r/memory/sessions/ capsule store, PRECEDES session lineage, and read/write verification gates." \
  --importance 0.85 \
  --tags "memorygraph,session,cr-memory-compound-001" \
  --relates-to "concept:tri-graph" \
  --relation DERIVES_FROM

hath0r memory session end --summary "Merged and verified micro memory session lifecycle"
hath0r memory verify
```

### Recipe C: Auditing & Synchronizing Cryptographic File Hashes (`hashes.json`) & Git Graph Tracking
```bash
# Audit all .hath0r/memory/ files, referenced repo source_files, and verify zero graph folders are gitignored
hath0r memory hash --check

# Re-hash and synchronize .hath0r/memory/hashes.json (also sanitizes .gitignore so graph folders are never ignored)
hath0r memory hash --sync --track-file "src/hath0r_engine/memory/memory_graph.py"
```

### Recipe D: Provisioning `.hath0r/memory`, `.hath0r/memory/sessions`, `.hath0r/memory/hashes.json` & Un-Ignoring Graph Folders Across All Repositories
```bash
hath0r memory ensure-all --root /Users/raybayly/Development
```

