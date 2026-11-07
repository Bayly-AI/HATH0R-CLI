# Procedure: HATH0R CLI Voice Command Usage

> Document Type: **Procedure** (`cr-workflow-doc-001`)  
> Product: **HATH0R-CLI** · Issue: #131 · SemVer: `minor`

## 1. Scope

Normative procedure for operators and agents invoking the `hath0r voice` command group.

## 2. Invocations

### Inspect Subsystem Status
```bash
hath0r voice status
hath0r --output json voice status
```

### Execute One-Shot Voice Action
```bash
# Diagnostic command (allowed in guest, elevated, sovereign)
hath0r voice exec "hath0r doctor"

# Desktop automation (allowed in elevated, sovereign)
hath0r voice exec "open Slack" --trust-tier elevated

# Dry run simulation
hath0r voice exec "hath0r version" --dry-run
```

### Interactive Continuous Listening
```bash
# Push-to-talk loop
hath0r voice listen --push-to-talk

# Ambient capture
hath0r voice listen --max-utterances 3
```
