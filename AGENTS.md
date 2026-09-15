# AGENTS.md — HATH0R CLI

> Role: **Operator / developer CLI (hath0r)** · member of group `hath0r-opensource`  
> Updated: 2026-09-15

## Group membership (CRITICAL)

| Field | Value |
|-------|-------|
| Group | `hath0r-opensource` |
| Group root | `/Users/raybayly/Development/OpenSource` |
| This product | `HATH0R-CLI` |
| GitHub | `Bayly-AI/HATH0R-CLI` |
| Local path | `/Users/raybayly/Development/OpenSource/HATH0R-CLI` |
| Canonical KB | `/Users/raybayly/Development/OpenSource/.hath0r/knowledgebase` |
| Operator CLI | `hath0r` |
| KB mode | stub |

### Canonical siblings

- Framework: `/Users/raybayly/Development/OpenSource/hath0r` → `Bayly-AI/HATH0R-Agentic-Framework`
- CLI: `/Users/raybayly/Development/OpenSource/HATH0R-CLI` → `Bayly-AI/HATH0R-CLI`
- POC: `/Users/raybayly/Development/OpenSource/hath0r-poc` → `Bayly-AI/HATH0R-Agentic-POC`

Group rules: `/Users/raybayly/Development/OpenSource/AGENTS.md`  
Group policy: `/Users/raybayly/Development/OpenSource/WARP.md`

## Framework hidden root (CRITICAL — cr-hath0r-root-001)

Use **only** `.hath0r/` for framework-created / modified / saved project metadata (including this repo’s KB stub).

Do **not** use `.ai/`, `.aegis/`, or `.infraOS/`.

## Knowledgebase (CRITICAL — cr-kb-tower-001)

1. Point local knowledgebase operations at the OpenSource group hub.
2. Keep `.hath0r/knowledgebase` as stub/pointer only (see README there).
3. Framework `docs/` is the **canonical OpenSource documentation** corpus.
4. Do **not** treat private internal product trees as OpenSource canonical sources.

## Branch & PR targets (CRITICAL — cr-branch-gov-001)

1. **Issue first**: create a GitHub issue before any work branch. No issue → no branch.
2. Branch from `development` only, using:
   `feature|bugfix|enhancement|research|fix|chore/<issue-number>-short-slug`
   Example: `chore/1-branch-protection-governance`
3. Open the PR with **base = `development`** (feature work never targets testing/staging/master).
4. **Owner approval required** before merge (`@somesayray` via CODEOWNERS + branch protection).
5. Merge into **`development` only** for feature work.
6. Promote via `development → testing → staging → master` — do not skip stages.

### Canonical branches (locked)

`development` (default), `testing`, `staging`, `master`

- Must not be deleted
- Must not be used as feature/work branches
- Must not be merged into each other except along the promotion path above
- Branch protection: PR required, 1 approving review, code-owner review, no force-push, no deletions, `validate-promotion-path` required

Forbidden: feature PRs targeting `master`, `testing`, or `staging`; PRs without an issue number in the branch name; merging canonical branches sideways.

## Config pointers in this repo

- `cfg/suite.yaml`
- `cfg/knowledge-tower.yaml`
- `.hath0r/knowledgebase/README.md`

## CR-BAI-001: Environment Promotion Path (CRITICAL — org-wide)

Canonical policy: `/Users/raybayly/Development/BAI/WARP.md`

Required order (never skip):

```text
local → development → testing → staging → master (Production)
```

CI enforcement: `.github/workflows/enforce-promotion-path.yml`

- PRs into `testing` must come from `development`
- PRs into `staging` must come from `testing`
- PRs into `master` must come from `staging`
- Each stage needs deploy + URL validation before the next promote

## Credentials

`/Users/raybayly/Development/.credentials/<service>/.env` — never hardcode or print secrets.
