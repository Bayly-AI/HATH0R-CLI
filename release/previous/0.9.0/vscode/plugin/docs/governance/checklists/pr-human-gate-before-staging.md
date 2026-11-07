# Checklist: HUMAN GATE before staging

**Automation and agent review STOP here. A human initiates staging.**

- [ ] Testing environment validated (functional + smoke)
- [ ] No open Sev-1/Sev-2 on testing build
- [ ] Human owner named for staging deploy
- [ ] Release PR base = `staging`
- [ ] Head = `testing` or `release/x.x.x`
- [ ] GitHub Environment `staging` approval by human (`@somesayray` or designated)
- [ ] Change window / communications done if required
- [ ] Rollback plan attached to PR
