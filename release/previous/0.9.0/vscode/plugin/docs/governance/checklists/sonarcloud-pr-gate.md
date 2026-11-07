# Checklist: SonarCloud PR Quality Gate

- [ ] `SONAR_TOKEN` configured (repo or org secret)
- [ ] `SONAR_ORGANIZATION` set if not default
- [ ] `sonar-project.properties` has identity/sources only (no local gate threshold overrides)
- [ ] Workflow `.github/workflows/sonarcloud-quality-gate.yml` present
- [ ] Branch protection requires check **SonarCloud Quality Gate** (where plan allows)
- [ ] Sample PR shows check; failed gate blocks merge
- [ ] PR template / AGENTS mention Sonar hard stop
- [ ] Docs published / linked for agents
