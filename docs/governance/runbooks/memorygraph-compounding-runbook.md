# MemoryGraph Compounding & Micro Memory Session Runbook

> **Rule Binding**: `CR-MEMORY-COMPOUND-001`  
> **Service / Component**: `hath0r memory` · `hath0r memory session` · `MemoryManagerBot` · `TaskAnnouncerBot`

## 1. Health, Session & Gate Verification

Check the current repository's `MemoryGraph` health, active micro-session state, and pre-announcement gate status:
```bash
hath0r memory session status
hath0r memory session read
hath0r memory verify
hath0r memory search
hath0r agentgraph status
```

Audit and provision `.hath0r/memory/` and `.hath0r/memory/sessions/` across all repositories in `/Users/raybayly/Development`:
```bash
hath0r memory ensure-all --root /Users/raybayly/Development
```

## 2. Troubleshooting & Remediation

### Issue 1: `TaskAnnouncerBot` Blocks Announcement (`SESSION_NOT_READ_OR_WRITTEN` or `MEMORY_NOT_COMPOUNDED`)
- **Symptom**: `announce-complete` or `hath0r memory verify` returns `success: False` indicating either no task knowledge was compounded into `.hath0r/memory/graph.json`, or the micro-session has `read_count < 1` or `write_count < 1`.
- **Remediation**:
  1. Ensure the micro-session has been read and written:
     ```bash
     hath0r memory session read
     hath0r memory session write "Completed task implementation and verification" --kind milestone
     ```
  2. Compound durable task knowledge into `graph.json`:
     ```bash
     hath0r memory compound --label "<Task Title>" --content "<Summary of learnings/changes>" --type episode --tags "<tags>"
     ```
  3. Verify with `hath0r memory verify`.
  4. Re-run `hath0r task finish` or completion announcement.

### Issue 2: Repository Missing `.hath0r/memory/graph.json` or `.hath0r/memory/sessions/current.json`
- **Symptom**: Repository has no `.hath0r/memory/sessions/` directory or `graph.json`.
- **Remediation**:
  ```bash
  hath0r memory init
  hath0r memory session start --focus "Initial repository session"
  ```
  Or remediate all repositories at once:
  ```bash
  hath0r memory ensure-all --root /Users/raybayly/Development
  ```

### Issue 3: `AgentGraph` Missing Memory Plane Nodes or Has Dangling Memory Edges
- **Symptom**: `hath0r agentgraph validate` reports dangling edges from `memory:` nodes or `hath0r agentgraph query --plane memory` returns stale results.
- **Remediation**:
  ```bash
  hath0r agentgraph sync
  hath0r agentgraph heal
  hath0r agentgraph validate
  ```

### Issue 4: Stale File Hash (`STALE_FILE_HASH`) or Concurrent Write Conflict (`HASH_CONFLICT`)
- **Symptom**: `hath0r memory verify` or `hath0r memory hash --check` reports that a file in `.hath0r/memory/` or a tracked `source_files` path has diverged from `.hath0r/memory/hashes.json`, or a write with `--expected-hash` returned `HASH_CONFLICT`.
- **Remediation**:
  1. Inspect which files changed or conflicted:
     ```bash
     hath0r memory hash --check
     ```
  2. Read the latest state, compound any updated knowledge if a tracked source file changed, and synchronize the hash manifest:
     ```bash
     hath0r memory session read
     hath0r memory hash --sync
     hath0r memory verify
     ```

