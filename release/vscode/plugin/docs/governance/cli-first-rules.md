# CLI-first & missing capability offer (cr-cli-first-001)

> Control tower: `Bayly-AI/HATH0R-CLI` · Issue track: #61  
> Binding agent rule also mirrored in root `AGENTS.md`.

## Rules

1. **CLI-first** — For connections, MCP, workflows, factories, Docker workflows, KB path, or suite orientation, invoke **`hath0r`** (or the documented operator entrypoint) instead of ad-hoc scripts.
2. **Missing capability offer** — If the required connection/MCP/workflow/factory does not exist, do **not** silently improvise. Offer to:
   - create/register the missing capability, and
   - use the original user request as the acceptance test.
3. **Session start** — Follow `docs/governance/checklists/agent-session-start.md`.
4. **Docs before code** — Procedure/strategy/playbook/runbook before scaffolding new implementation (`workflow-documentation-standard.md`).

## Discoverability

| Surface | Location |
|---------|----------|
| Agent rules | `AGENTS.md` (CLI-First section) |
| Group policy | `cfg/group/WARP.md` / OpenSource `WARP.md` |
| Session checklist | `docs/governance/checklists/agent-session-start.md` |
| This standard | `docs/governance/cli-first-rules.md` |

## Example offer language

> The project MCP connection is not registered. I can add it to `cfg/mcp.servers.json` (priority-ordered), validate with `hath0r mcp check`, then re-run your original request as the acceptance test. Proceed?

## Acceptance

- [x] Rules present in `AGENTS.md`
- [x] Session checklist exists and references CLI-first
- [x] This doc is linked from governance index / WARP mirror note
