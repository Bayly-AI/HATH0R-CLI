# Playbook: Hath0r Automatic Task Evaluations (`CR-TASK-EVAL-001`)

> Canonical Operator & Agent Playbook · ID: `PB-TASK-EVAL-001`  
> Epic: #510 · CLI Entrypoint: `hath0r evals`

---

## 1. Quick Reference Commands

```bash
# Run full 4-tier evaluation on the current workspace and persist scorecard
hath0r evals run

# Run fast evaluation (skip full pytest suite re-run if already verified)
hath0r evals run --skip-tests

# Inspect the latest evaluation scorecard and tier breakdown
hath0r evals status

# Verify that the current workspace has a valid passing evaluation before announcing complete
hath0r evals verify

# Generate suite-wide evaluation summary across repositories and MLflow/Phoenix
hath0r evals report
```

---

## 2. Remediating Evaluation Gate Failures

### Case A: Tier 1 Failure (`DeterministicRubric`)
- **Symptom**: `Preflight`, `Tests`, `AgentGraph`, or `MemoryGate` failed.
- **Remediation**:
  1. Run `pytest` and `ruff check src` to fix unit test or lint errors.
  2. Ensure `VERSION` and `CHANGELOG.md` are updated (`CR-SEMVER-BUMP-001`).
  3. Run `hath0r agentgraph validate` and `hath0r memory verify` to ensure `.hath0r/memory/graph.json` and `hashes.json` are synchronized.

### Case B: Tier 2 Failure (`TrajectoryEfficiency` / `FinOps`)
- **Symptom**: `TokenBudgetExceeded` or micro-session capsule exceeds 2048 bytes.
- **Remediation**:
  1. Check budget status via `hath0r finops budget check`.
  2. Compact micro-session via `hath0r memory session write --summary "..."`.

### Case C: Tier 3 Failure (`AntagonisticDiffCritic`)
- **Symptom**: `SwallowedException` (`except Exception: pass`) or untracked `TODO`/`FIXME` marker in git diff.
- **Remediation**:
  1. Replace bare `except Exception: pass` with explicit error handling or logging.
  2. Resolve `TODO`/`FIXME` markers or hand them off to GitHub Issues (`CR-CLI-TECH-DEBT-001`).
