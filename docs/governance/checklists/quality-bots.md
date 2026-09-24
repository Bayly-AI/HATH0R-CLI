# Checklist — Quality / Factory / Release bots

- [ ] `cfg/quality-gates.json` present; hard_gates list reviewed
- [ ] `hath0r factory validate` green (includes quality-release-factory)
- [ ] `hath0r factory create demo-factory --dry-run` succeeds
- [ ] `hath0r preflight run --skip-tests` on a valid work branch
- [ ] `hath0r quality check <pr> --dry-run`
- [ ] `hath0r release validate` (VERSION + CHANGELOG)
- [ ] `hath0r docs share --pr N --dry-run`
- [ ] `hath0r docs wiki --repo owner/repo --title t --dry-run` (skipped unless wiki.enabled)
- [ ] No secrets in factory YAML or quality-gates.json
- [ ] SonarCloud remains the only coverage threshold source
