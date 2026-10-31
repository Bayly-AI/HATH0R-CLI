# MCP Centralization & Workflow-First Standard (`CR-FEATURE-WORKFLOW-STANDARD-001`)

> **Governance Hexad**: Strategy · Procedure · Playbook · Runbook · Workflow · Bot Specification  
> **Owning Bots**: `MCPCentralizationBot` (`mcp-centralization-bot`), `MCPWorkflowEngineBot` (`mcp-workflow-engine-bot`)  
> **Declarative Factory**: [`cfg/factories/workflow-first-offer-factory.yaml`](../../cfg/factories/workflow-first-offer-factory.yaml)

## 1. Strategy
Enforce `CR-FEATURE-WORKFLOW-STANDARD-001` and `CR-MCP-CENTRAL-001` across the Hath0r OpenSource Suite:
- **Every Feature Is a Service Run by `>= 1` Bot**: Every CLI command group and MCP tool maps to `>= 1` registered Bot in `BotRegistry`.
- **Two-Level Topology on `AgentGraph`**:
  - **Level 1 (`HATH0R-MCP`)**: Central tools, workflows, factories, and suite knowledge (`http://127.0.0.1:38083`).
  - **Level 2 (`HATH0R-CLI` & `.hath0r/memory/`)**: Operator CLI execution (`hath0r`) and Bot Memory (`MemoryGraph`), synchronized with Level 1 via `AgentGraph`.
- **Workflow-First Standard ("Everything We Do Is a Workflow")**: Every task executes as a declarative workflow; if a workflow is missing, `MCPWorkflowEngineBot` halts ad-hoc execution and offers to create and scaffold the workflow first (`hath0r workflow offer` / `hath0r workflow scaffold`) using the original request as its acceptance test.

## 2. Procedure & Playbook
1. Verify 4-hour agent calibration (`hath0r cccd status` / `ensure_calibrated(max_age_hours=4.0)`).
2. Audit Level 1 & Level 2 parity (`hath0r mcp parity`) and pin pruned tool schemas (`hath0r mcp pin-schemas` → `.hath0r/security/mcp-schema-pins.json`).
3. Match task intent (`hath0r workflow match --intent "<request>"`).
4. When unmatched, offer and scaffold the missing workflow (`hath0r workflow offer --intent "<request>"` → `hath0r workflow scaffold --intent "<request>"`).

## 3. Runbook & Bot Specification
- **`MCPCentralizationBot`** (`src/hath0r_cli/bots/mcp_centralization_bot.py`): `audit_parity()`, `prune_and_pin_schemas()`, `sync_level1_level2_agentgraph()`.
- **`MCPWorkflowEngineBot`** (`src/hath0r_cli/bots/mcp_workflow_engine_bot.py`): `list_workflows()`, `match_workflow()`, `offer_missing_workflow()`, `scaffold_workflow()`, `execute_workflow_first()`.
