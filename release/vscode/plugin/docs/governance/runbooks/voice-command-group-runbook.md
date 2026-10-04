# Runbook: HATH0R CLI Voice Command Operations

> Document Type: **Runbook** (`cr-workflow-doc-001`)  
> Product: **HATH0R-CLI** · Issue: #131 · SemVer: `minor`

## 1. Quick Operations Commands

### Run Voice CLI Unit Tests
```bash
python3 -m pytest tests/cli/test_voice.py -v
```

### Smoke Test Voice Status
```bash
python3 -m hath0r_cli.cli voice status
```

### Smoke Test Fast-Path Execution Under 50ms
```bash
python3 -m hath0r_cli.cli -o json voice exec "hath0r doctor" --dry-run
```
