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

1. Create a **feature / fix / chore branch** from `development`
2. Open the PR with **base = `development`**
3. Merge into **`development` only**
4. Promote via `development → testing → staging → master` — do not skip stages

Forbidden: feature PRs targeting `master`, `testing`, or `staging`.

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
