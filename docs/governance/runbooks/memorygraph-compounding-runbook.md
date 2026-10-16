# MemoryGraph Compounding & Pre-Announcement Gate Runbook

> **Rule Binding**: `CR-MEMORY-COMPOUND-001`  
> **Service / Component**: `hath0r memory` · `MemoryManagerBot` · `TaskAnnouncerBot`

## 1. Health & Gate Verification

Check the current repository's `MemoryGraph` health and pre-announcement gate status:
```bash
hath0r memory verify
hath0r memory search
hath0r agentgraph status
```

Audit all repositories in `/Users/raybayly/Development`:
```bash
hath0r memory ensure-all --root /Users/raybayly/Development
```

## 2. Troubleshooting & Remediation

### Issue 1: `TaskAnnouncerBot` Blocks Announcement (`MEMORY_NOT_COMPOUNDED`)
- **Symptom**: `announce-complete` returns `success: False` with error indicating no task knowledge has been compounded into `.hath0r/memory/graph.json`.
- **Remediation**:
  1. Run `hath0r memory compound --label "<Task Title>" --content "<Summary of learnings/changes>" --type episode --tags "<tags>"`
  2. Verify with `hath0r memory verify`.
  3. Re-run `hath0r task finish` or completion announcement.

### Issue 2: Repository Missing `.hath0r/memory/graph.json`
- **Symptom**: Repository has no `.hath0r/memory` directory or only markdown files without `graph.json`.
- **Remediation**:
  ```bash
  hath0r memory init
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
