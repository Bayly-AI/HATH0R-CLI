# Playbook: Dynamic Tool Routing & Schema Pruning Operations

> Operational Playbook for Dynamic Tool Selection & Schema Optimization  
> Product: `HATH0R-CLI` · Group: `hath0r-opensource` · Issue: #224

---

## 📋 Overview

This playbook describes how to configure, route, and prune tool schemas in `HATH0R-CLI` using the `hath0r mcp route` and `hath0r mcp prune` subcommands or programmatically via `DynamicToolRouter` and `SchemaPruner`.

---

## 🛠️ CLI Operations

### 1. Route Tools for a Given Task Intent
To find the top-K tools matching an intent:

```bash
hath0r mcp route --intent "validate git branch and open pull request" --top-k 3
```

### 2. Prune Verbose Tool Schemas
To compress a tool schema JSON file:

```bash
hath0r mcp prune --input-file schema.json --output-file pruned_schema.json
```

---

## 💻 Programmatic Integration

```python
from hath0r_cli.mcp import DynamicToolRouter, SchemaPruner

tools = [...]  # full list of MCP / bot tool declarations
router = DynamicToolRouter(tools)
active_tools = router.route("inspect image architecture diagram", top_k=3)

pruner = SchemaPruner()
compressed_tools = [pruner.prune(t) for t in active_tools]
```
