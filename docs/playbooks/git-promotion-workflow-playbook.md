# Git Workflow & Environment Promotion — Playbook

| Symptom | Cause | Response |
|---------|-------|----------|
| `validate-promotion-path` fails on a PR | Head/base not allowed | `hath0r pr check --head … --base …` shows the rule; retarget the PR or promote via the previous stage. |
| `Invalid work branch` | Name lacks `<type>/<issue>-slug` | Create the issue, then `hath0r branch start`; push work there. |
| Push to testing/staging/master rejected (ancestry) | Promotion PR was squashed | Re-promote from the previous stage with a merge commit (`hath0r pr merge` does this automatically). |
| `branch sync` reports conflicts | Upstream changed the same files | Tree is restored. Run `git merge origin/development`, resolve, commit. |
| `promote to` says *already contains everything* | Nothing pending | No action; check `hath0r promote status`. |
| `pr merge` refuses staging/master | Human gate | Get human review/approval, then rerun with `--human-approved`. |
| `promote release` warns VERSION mismatch | `VERSION` on development differs | Bump `VERSION`/`CHANGELOG.md` on development (or a release fix PR) before promoting. |
| Large **drift** on a stage | Hotfix landed downstream | Open a work PR back-merging the hotfix into `development`. |
