# Runbook: Repository Hygiene Operations

> Document Type: **Runbook** (`cr-workflow-doc-001`)  
> Product: **HATH0R-CLI** · Issue: #135 · SemVer: `minor`

## 1. Routine Verification

Run cleanliness audit during daily workflow or preflight gates:
```bash
hath0r repo audit
```

If issues are found:
- **Misplaced Root Configs**: Review listed files, run `hath0r repo clean` to relocate eligible configs to `.cfg/`.
- **Errant Files**: Review unexpected root files and archive/delete as appropriate.
- **Monolithic Documents**: Review oversized markdown files flagged by `KnowledgeOrganizerBot` and partition into topic folders.

## 2. Emergency Recovery

If a file was moved inadvertently:
- Use `git status` / `git diff` to inspect changes.
- Revert or adjust the allowable file configuration.
