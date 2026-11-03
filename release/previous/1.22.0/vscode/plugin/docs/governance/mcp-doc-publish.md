# Share documentation to proper MCPs (ticket 4)

## Mapping
| Group | MCP | Local default |
|-------|-----|---------------|
| Hath0r / OpenSource | Hath0r MCP / hub | `OpenSource/hath0r-mcp` or `.hath0r/knowledgebase` |
| BAI | `Bayly-AI/BAI-MCP` | `BAI/MCP` |
| 1-Nation | `Bayly-AI/1-Nation-MCP` | `1-Nation/MCP` |

## Tooling
- Config: `cfg/mcp-doc-publish.json`
- Script: `scripts/publish-docs-to-mcp.py`
- CI: `.github/workflows/publish-docs-to-mcp.yml`

## Policy
- Proper group MCP only; no BAI → OpenSource cross-publish.
- Secrets never published.
