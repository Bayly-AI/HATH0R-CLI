# Procedure: CLI Update Standardization

> Standard operating procedure for engineers and agents delivering modifications to `hath0r`.

---

## 1. Prerequisites
- `hath0r` CLI installed and linked locally (`pip install -e ".[dev]"`).
- Branch created following `cr-branch-gov-001` rules.
- Working tree clean.

---

## 2. Procedure Steps

| Step | Action | Command | Responsible Bot |
|---|---|---|---|
| 1 | Health Check | `hath0r doctor` | `preflight-bot` |
| 2 | Code & Tests | `pytest tests/` | `quality-gate-bot` |
| 3 | SemVer Sync | `hath0r version check` | `version-bot` |
| 4 | Doc Refactor | Update `README.md`, `TECH_README.md`, `CHANGELOG.md` | `doc-refactor-bot` |
| 5 | Memory Ingest | `hath0r memory init` | `tri-graph-ingest-bot` |
| 6 | Release Check | `hath0r release validate` | `release-bot` |
| 7 | Governed PR | `gh pr create --base development` | `git-pr-bot` |
| 8 | Announce | Telemetry event logged | `task-announcer-bot` |

---

## 3. Rollback & Remediation
If any validation step fails, the pipeline aborts immediately without opening a pull request. Fix the underlying test or documentation deficiency and re-run.
