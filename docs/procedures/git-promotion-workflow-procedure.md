# Git Workflow & Environment Promotion — Procedure

1. **Issue first.** Create or pick an open GitHub issue (`hath0r issue create …`).
2. **Start the branch:** `hath0r branch start feature 42 "add kb sync"` → `feature/42-add-kb-sync` from `origin/development`
   (verifies issue #42 is open; `--no-issue-check` to skip, `--dry-run` to preview).
3. **Keep current:** `hath0r branch sync` (merge) or `hath0r branch sync --rebase`.
4. **Bump version** (`VERSION`, `pyproject.toml`, `CHANGELOG.md`) per CR-SEMVER-BUMP-001.
5. **Open the work PR:** `hath0r pr create --semver minor` — validates the path, pushes, writes `Closes #42` and `Version Impact`.
6. **Watch checks:** `hath0r pr status <n>`; then `hath0r pr merge <n>` (squash + delete branch).
7. **Optional release branch:** `hath0r promote release 1.13.0`.
8. **Promote to testing:** `hath0r promote to testing [--from release/1.13.0] [--gate]` → merge with `hath0r pr merge <n>`.
9. **Human gate — staging:** `hath0r promote to staging --gate`; after human review `hath0r pr merge <n> --human-approved`.
10. **Human gate — production:** `hath0r promote to production --gate`; after human review `hath0r pr merge <n> --human-approved`.

Check the pipeline at any time with `hath0r promote status`. Every command supports `-o json`.
