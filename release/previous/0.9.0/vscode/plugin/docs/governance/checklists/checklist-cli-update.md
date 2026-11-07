# Checklist: CLI Update Completion

> Checklist to verify before approving and merging CLI updates.

---

- [ ] Working branch is named following `feature|bugfix|enhancement/<issue>-<slug>`.
- [ ] `hath0r doctor` passes with zero failed checks.
- [ ] All unit and integration tests pass (`pytest tests/`).
- [ ] `VERSION`, `pyproject.toml`, and `CHANGELOG.md` are synchronized.
- [ ] `README.md` and `TECH_README.md` reflect all newly introduced commands/features.
- [ ] Tri-Graph memory substrate has ingested updated docs (`.hath0r/memory/graph.json`).
- [ ] Release package validation passes (`hath0r release validate`).
- [ ] PR targets base branch `development`.
