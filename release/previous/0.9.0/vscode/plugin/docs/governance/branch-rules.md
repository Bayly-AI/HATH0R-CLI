# Branch rules (cr-branch-gov-001 / CR-BAI-001)

> Control tower source: `Bayly-AI/HATH0R-CLI`  
> Applies org-wide to Hath0r/OpenSource, BAI, and 1-Nation product repos.  
> Issue track: define-branch-rules (all-repos)

## Locked canonical branches

| Branch | Role | Protection |
|--------|------|------------|
| `development` | Default integration; **only** target for work PRs | PR + 1 review + CODEOWNERS + `validate-promotion-path` + no force-push/delete |
| `testing` | Pre-staging validation | Same; heads: `development` or `release/x.x.x` |
| `staging` | Pre-production | Same; heads: `testing` or `release/x.x.x`; **human review** |
| `master` | Production | Same; heads: `staging` or `release/x.x.x`; **human review** |

## Work branches (PR → `development` only)

```text
feature|bugfix|hotfix|enhancement|research|fix|chore/<issue-number>-short-slug
```

- Create a GitHub **issue first** (no issue → no branch).
- Branch **from `development` only**.
- **Never** open work PRs into `testing`, `staging`, or `master`.

## Release branches

```text
release/x.x.x
```

Examples: `release/1.4.0`, `release/2.0.0-rc.1`

- Cut from `development` when a release train starts.
- Used **only** for promotion beyond development (not feature work).
- CI allows `release/x.x.x` → `testing` / `staging` / `master` per stage rules.

## Promotion path

```text
local → work branch → PR → development
                      ↓
                 release/x.x.x (optional cut)
                      ↓
                   testing  →  staging  →  master
```

Never skip stages. Do not merge canonical branches sideways.

## CI

Workflow: `.github/workflows/enforce-promotion-path.yml`  
Required check context: **`validate-promotion-path`**

## CODEOWNERS

`.github/CODEOWNERS` must include default owner `@somesayray`.

## Private repositories

GitHub **classic branch protection** on private repositories requires an org plan that includes that feature (GitHub Team/Enterprise or public repos). Where the API returns HTTP 403 (“Upgrade to GitHub Pro…”):

1. Still ship `enforce-promotion-path.yml` + `CODEOWNERS` (CI gate).
2. Track org plan upgrade or make the repo public if policy allows.
3. Operators must not force-push/delete canonical branches manually.

## Checklist

- [ ] Canonical branches exist: development, testing, staging, master
- [ ] Default branch = `development`
- [ ] CODEOWNERS present
- [ ] `enforce-promotion-path.yml` present
- [ ] Branch protection applied (or private-repo limitation documented)
- [ ] AGENTS.md / WARP.md document work vs release branch rules
