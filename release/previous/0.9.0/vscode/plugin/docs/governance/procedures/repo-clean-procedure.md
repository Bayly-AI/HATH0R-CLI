# Procedure: Repository Cleanliness & Organization Execution

> Document Type: **Procedure** (`cr-workflow-doc-001`)  
> Product: **HATH0R-CLI** · Issue: #135 · SemVer: `minor`

## 1. Scope

Normative operational steps for executing the `repo-clean-factory` workflows and CLI commands.

## 2. Invocations

### Audit Cleanliness (Non-mutating)
```bash
# Run via CLI domain command:
hath0r repo audit

# Or run via factory orchestrator:
hath0r factory run repo-clean-factory --workflow audit-cleanliness
```

### Organize Cleanliness (Remediation)
```bash
# Dry-run inspection of moves/archivals:
hath0r repo clean --dry-run

# Execute organization:
hath0r repo clean

# Or run via factory orchestrator:
hath0r factory run repo-clean-factory --workflow organize-cleanliness
```
