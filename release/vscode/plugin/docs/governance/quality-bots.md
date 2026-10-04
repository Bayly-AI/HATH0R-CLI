# Quality, Factory Manager, Release, and Docs bots

> Control tower: `Bayly-AI/HATH0R-CLI`  
> Issues: #64, #66, #67, #68, #69, #70, #71  
> Config: `cfg/quality-gates.json`, `cfg/factories/quality-release-factory.yaml`

## Commands

| Command | Purpose |
|---------|---------|
| `hath0r factory create\|update\|delete\|list\|info\|validate\|run` | Factory Manager CRUD + execute |
| `hath0r preflight run` | Pre-PR thresholds (branch, VERSION, local tests) |
| `hath0r deploy pre\|post` | Pre/post-deploy tests |
| `hath0r quality check <pr>` | Aggregate hard gates incl. SonarCloud |
| `hath0r release validate\|notes\|publish` | SemVer + CHANGELOG + tag/release |
| `hath0r docs wiki` | PR → GitHub wiki (cfg dual-enable) |
| `hath0r docs share` | Post-PR knowledge → project MCP/KB |

## Hard gates

Default names (override in `cfg/quality-gates.json`):

- `SonarCloud Quality Gate` (canonical coverage/ratings — do not invent local thresholds)
- `validate-promotion-path`
- `pr-workflow-guard`

## Wiki dual enablement

Wiki sync runs only when **both**:

1. `cfg/quality-gates.json` → `wiki.enabled: true`
2. GitHub wiki is enabled on the target repo

Use `--force` for operator override. Pages are idempotent by PR number (`PR-<n>-…`).

## Knowledge share

Writes durable markdown under the project MCP local path from `cfg/mcp-doc-publish.json` (hath0r group first). Keyed by `pr-<n>.md`.

## Checklist

See `docs/governance/checklists/quality-bots.md`.

## Test-doc

See unit tests in `tests/unit/test_quality_bots.py`.
