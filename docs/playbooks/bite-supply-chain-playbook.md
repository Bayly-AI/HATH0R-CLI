# Playbook: Agentic Supply-Chain & Knowledge Curation Verification (`CR-AGENTIC-SEC-001`)

## When to Run
- Before installing or enabling a new `SKILL.md`, `AGENTS.md`, or MCP server in `.hath0r/mcp.json`.
- During `hath0r preflight` and `hath0r evals run` pre-announcement gates.

## Step-by-Step Execution
1. Run `hath0r skills audit` and confirm `summary.dangerous == 0`.
2. Run `hath0r mcp audit` and confirm all configured MCP servers pass BITE verification.
3. Run `hath0r threatmodel validate` to ensure `THREATMODEL.md` passes fail-closed validation.
4. Run `hath0r finops tokens verify-ledger` to verify SHA-256 hash chain continuity.
5. Run `hath0r kb redteam` to confirm zero unredacted secret or PII leaks across personas.
