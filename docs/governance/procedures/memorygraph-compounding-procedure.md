# MemoryGraph Compounding Standard Operating Procedure

> **Rule Binding**: `CR-MEMORY-COMPOUND-001`  
> **CLI Entrypoint**: `hath0r memory`

## 1. Purpose

Defines the mandatory step-by-step procedure for initializing `.hath0r/memory/`, compounding task knowledge into `.hath0r/memory/graph.json`, synchronizing `.hath0r/agentgraph/snapshot.json`, and verifying the pre-announcement gate before declaring any task complete.

## 2. Procedure Steps

### Step 1: Verify or Initialize Repository Memory Space
At the start of orientation or repository hygiene, ensure `.hath0r/memory/graph.json` exists:
```bash
hath0r memory init
# Or across all repositories in a workspace/suite:
hath0r memory ensure-all --root /Users/raybayly/Development
```

### Step 2: Query Existing Memory Prior to Implementation
Retrieve relevant episodic learnings, architectural decisions, and insights:
```bash
hath0r memory search "<topic>"
hath0r agentgraph query "<topic>" --plane memory
```

### Step 3: Compound Knowledge Prior to Announcing Complete
Before calling `hath0r task finish` or announcing task completion to the operator, record the task's architectural decisions, root-cause fixes, or episodic outcomes:
```bash
hath0r memory compound \
  --label "Short descriptive title of learning or decision" \
  --content "Detailed summary of what was built, fixed, or decided and why." \
  --type episode \
  --tags "memorygraph,governance,cli" \
  --relates-to "concept:tri-graph" \
  --relation DERIVES_FROM
```

### Step 4: Verify Pre-Announcement Memory Gate
Run the deterministic gate verification check:
```bash
hath0r memory verify
```
 Confirm that:
- `.hath0r/memory/graph.json` is valid.
- At least one non-seed compounded node (`episode`, `decision`, `fact`, `insight`) is recorded.
- `.hath0r/agentgraph/snapshot.json` is synchronized with the `memory` plane.

### Step 5: Execute End-of-Task / Announce Complete
Proceed with `hath0r task finish` or `TaskAnnouncerBot.announce_complete()`, which enforces `verify_compounded()` prior to announcing completion.
