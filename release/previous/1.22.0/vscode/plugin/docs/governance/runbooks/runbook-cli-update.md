# Runbook: CLI Update Operations

> Operations runbook for running `update-cli-factory` and handling edge cases.

---

## 1. Quick Invocation

```sh
hath0r factory run update-cli-factory
```

---

## 2. Dry-Run Execution

To simulate the entire update workflow without making commits or mutations:

```sh
hath0r factory run update-cli-factory --dry-run
```

---

## 3. Troubleshooting Common Failure Modes

### Test Failure in `quality-gate-bot`
- **Symptom:** Step fails on `run-tests`.
- **Resolution:** Run `pytest tests/test_failing.py -v` directly to diagnose and correct broken assertions.

### Version Mismatch in `version-bot`
- **Symptom:** Step fails on `ensure-version`.
- **Resolution:** Verify `VERSION`, `pyproject.toml`, and `CHANGELOG.md` have identical version strings.

### Packaging Error in `release-bot`
- **Symptom:** Step fails on `validate`.
- **Resolution:** Check `CHANGELOG.md` contains an unreleased or corresponding release section matching `VERSION`.
