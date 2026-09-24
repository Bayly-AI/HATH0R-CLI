# Checklist: pre-merge → development

- [ ] Linked GitHub issue in branch name and PR body (`Fixes #N` / `Refs #N`)
- [ ] Branch named `feature|bugfix|hotfix|enhancement|research|fix|chore/<n>-slug`
- [ ] PR base is **`development`**
- [ ] Feature PR template completed
- [ ] `validate-promotion-path` green
- [ ] CI / tests green
- [ ] Quality gates (Sonar etc.) green when enabled
- [ ] CODEOWNERS review requested/approved
- [ ] No secrets in diff
- [ ] Docs/runbooks updated if workflow changed
