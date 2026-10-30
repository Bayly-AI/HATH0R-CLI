# Bot Specification: RuleRolloutBot

> Canonical Bot Specification · Updated: 2026-10-28 · Issue: #528

## 1. Role & Identity

- **Class**: `RuleRolloutBot` (`src/hath0r_cli/bots/rule_rollout_bot.py`)
- **CLI**: `hath0r rules list | status | ensure-all`
- **Function**: Rolls a canonical `CR-*` `AGENTS.md` section out to every repository remote under a workspace root, with SemVer bump, issue, and PR.

## 2. Actions

1. `list_rules()`: canonical sections shipped in `CANONICAL_RULE_SECTIONS`.
2. `status(rule_id, root)`: per-remote classification without writing.
3. `ensure_all(rule_id, root, section, apply, publish, ...)`: preview, prepare, or publish.

## 3. Reuse

- Repository discovery: `TaskEvaluatorBot._discover_repos` (skips `ARCHIVE`, `node_modules`, `.venv`).
- Release check: `ReleaseBot.validate`.
- Issue creation: `IssueManagerBot.create_issue`.

## 4. Guarantees

- Never edits a primary checkout. Work happens only in worktrees cut from `origin/development`.
- Never bypasses git hooks.
- Idempotent: compliant and pending-PR remotes are skipped.
