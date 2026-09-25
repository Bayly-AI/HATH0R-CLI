# Checklist: Repository Hygiene & Organization

> Document Type: **Checklist** (`cr-workflow-doc-001`)  
> Product: **HATH0R-CLI** · Issue: #135 · SemVer: `minor`

## Pre-Merge Cleanliness Verification

- [ ] Project root contains only canonical whitelisted files (`AGENTS.md`, `README.md`, `LICENSE`, `NOTICE`, `MANIFEST.json`, `VERSION`, `Makefile`, `pyproject.toml`, `pytest.ini`, `sonar-project.properties`, `CHANGELOG.md`).
- [ ] No errant dump, log, or scratch files at root.
- [ ] Auxiliary and non-standard config files are stored in `.cfg/` or `cfg/`.
- [ ] Knowledge, rules, and agent definitions are decomposed into topic folders, not bloated single documents.
- [ ] `hath0r repo audit` returns 0 violations or cleanly categorized warnings.
