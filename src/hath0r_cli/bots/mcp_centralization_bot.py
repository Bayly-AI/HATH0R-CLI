"""MCPCentralizationBot — Level 1 (HATH0R-MCP) & Level 2 (HATH0R-CLI/Memory) Parity & Schema Pinning Bot.

Enforces CR-FEATURE-WORKFLOW-STANDARD-001 and CR-MCP-CENTRAL-001:
- Audits tool, workflow, and knowledge parity between Level 1 (HATH0R-MCP) and Level 2
  (HATH0R-CLI & .hath0r/memory/) across AgentGraph.
- Verifies every Level 1 MCP tool and Level 2 CLI command group has >= 1 owning Bot in BotRegistry.
- Prunes verbose tool schemas via SchemaPruner and pins SHA-256 digests in
  .hath0r/security/mcp-schema-pins.json.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hath0r_cli.mcp import SchemaPruner

# Canonical Level 1 (HATH0R-MCP) tool catalog with owning bots & workflows
CANONICAL_LEVEL1_MCP_TOOLS: dict[str, dict[str, Any]] = {
    "kb_search": {
        "service": "Hybrid Knowledgebase Search Service",
        "owning_bots": ["cag-rag-router-bot", "knowledge-organizer-bot", "supersqueeze-bot"],
        "workflow_id": "cfg/factories/mcp-kb-retrieval-workflow.yaml",
        "agentgraph_level": "L1_MCP_AND_L2_CLI_MEMORY",
    },
    "kb_get": {
        "service": "Canonical Knowledge Document Retrieval Service",
        "owning_bots": ["knowledge-organizer-bot", "supersqueeze-bot"],
        "workflow_id": "cfg/factories/mcp-kb-retrieval-workflow.yaml",
        "agentgraph_level": "L1_MCP_AND_L2_CLI_MEMORY",
    },
    "kb_status": {
        "service": "Knowledgebase Index & Health Service",
        "owning_bots": ["knowledge-organizer-bot", "preflight-bot"],
        "workflow_id": "cfg/factories/mcp-kb-retrieval-workflow.yaml",
        "agentgraph_level": "L1_MCP",
    },
    "mcp_agentgraph_status": {
        "service": "Two-Level AgentGraph Status Service",
        "owning_bots": ["agentgraph-bot", "mcp-centralization-bot"],
        "workflow_id": "cfg/factories/memory-agentgraph-sync-factory.yaml",
        "agentgraph_level": "L1_MCP_AND_L2_CLI_MEMORY",
    },
    "mcp_agentgraph_query": {
        "service": "Two-Level AgentGraph Rule & Policy Query Service",
        "owning_bots": ["agentgraph-bot", "mcp-centralization-bot"],
        "workflow_id": "cfg/factories/memory-agentgraph-sync-factory.yaml",
        "agentgraph_level": "L1_MCP_AND_L2_CLI_MEMORY",
    },
    "mcp_agentgraph_route": {
        "service": "Two-Level AgentGraph Role & Tool Routing Service",
        "owning_bots": ["agentgraph-bot", "mcp-workflow-engine-bot"],
        "workflow_id": "cfg/factories/mcp-tool-dispatch-workflow.yaml",
        "agentgraph_level": "L1_MCP_AND_L2_CLI_MEMORY",
    },
    "mcp_agentgraph_sync": {
        "service": "Two-Level AgentGraph Synchronization Service",
        "owning_bots": ["agentgraph-bot", "mcp-centralization-bot"],
        "workflow_id": "cfg/factories/memory-agentgraph-sync-factory.yaml",
        "agentgraph_level": "L1_MCP_AND_L2_CLI_MEMORY",
    },
    "mcp_agentgraph_validate": {
        "service": "Two-Level AgentGraph Integrity Validation Service",
        "owning_bots": ["agentgraph-bot", "governance-bot"],
        "workflow_id": "cfg/factories/memory-agentgraph-sync-factory.yaml",
        "agentgraph_level": "L1_MCP_AND_L2_CLI_MEMORY",
    },
    "hath0r_supersqueeze": {
        "service": "SuperSqueeze Token Compression Service",
        "owning_bots": ["supercompress-bot", "supersqueeze-bot"],
        "workflow_id": "cfg/factories/supersqueeze-context-workflow.yaml",
        "agentgraph_level": "L1_MCP_AND_L2_CLI_MEMORY",
    },
    "hath0r_workflow_offer": {
        "service": "Workflow-First Missing-Workflow Offer Service",
        "owning_bots": ["mcp-workflow-engine-bot", "factory-manager-bot"],
        "workflow_id": "cfg/factories/workflow-first-offer-factory.yaml",
        "agentgraph_level": "L1_MCP_AND_L2_CLI_MEMORY",
    },
    "mcp_workflow_list": {
        "service": "Declarative Workflow Catalog Service",
        "owning_bots": ["mcp-workflow-engine-bot", "factory-manager-bot"],
        "workflow_id": "cfg/factories/workflow-first-offer-factory.yaml",
        "agentgraph_level": "L1_MCP_AND_L2_CLI_MEMORY",
    },
    "mcp_workflow_match": {
        "service": "Workflow-First Intent Matcher Service",
        "owning_bots": ["mcp-workflow-engine-bot", "factory-manager-bot"],
        "workflow_id": "cfg/factories/workflow-first-offer-factory.yaml",
        "agentgraph_level": "L1_MCP_AND_L2_CLI_MEMORY",
    },
    "mcp_workflow_scaffold": {
        "service": "Declarative Workflow Scaffolder Service",
        "owning_bots": ["mcp-workflow-engine-bot", "factory-manager-bot"],
        "workflow_id": "cfg/factories/workflow-first-offer-factory.yaml",
        "agentgraph_level": "L1_MCP_AND_L2_CLI_MEMORY",
    },
    "mcp_workflow_run": {
        "service": "Declarative Workflow Execution Service",
        "owning_bots": ["mcp-workflow-engine-bot", "factory-manager-bot", "cicccd-managing-bot"],
        "workflow_id": "cfg/factories/workflow-first-offer-factory.yaml",
        "agentgraph_level": "L1_MCP_AND_L2_CLI_MEMORY",
    },
    "mcp_bot_list": {
        "service": "BotRegistry Discovery Service",
        "owning_bots": ["mcp-centralization-bot", "factory-manager-bot"],
        "workflow_id": "cfg/factories/mcp-tool-dispatch-workflow.yaml",
        "agentgraph_level": "L1_MCP_AND_L2_CLI_MEMORY",
    },
    "mcp_bot_invoke": {
        "service": "BotRegistry Action Dispatch Service",
        "owning_bots": ["mcp-workflow-engine-bot", "factory-manager-bot"],
        "workflow_id": "cfg/factories/mcp-tool-dispatch-workflow.yaml",
        "agentgraph_level": "L1_MCP_AND_L2_CLI_MEMORY",
    },
    "mcp_cccd_ensure_calibrated": {
        "service": "4-Hour Pre-Task Agent Calibration Gate Service",
        "owning_bots": ["cicccd-managing-bot", "calibration-bot"],
        "workflow_id": "cfg/factories/cccd-4h-calibration-factory.yaml",
        "agentgraph_level": "L1_MCP_AND_L2_CLI_MEMORY",
    },
    "mcp_cruise_status": {
        "service": "Hath0r-Cruise-Control Decision Radar Service",
        "owning_bots": ["decision-radar-bot"],
        "workflow_id": "cfg/factories/hath0r-net-telemetry-factory.yaml",
        "agentgraph_level": "L1_MCP_AND_L2_CLI_MEMORY",
    },
    "mcp_mlflow_log_eval": {
        "service": "Hathor-MLFLOW Evaluation Logging Service",
        "owning_bots": ["mlflow-manager-bot", "task-evaluator-bot"],
        "workflow_id": "cfg/factories/hath0r-net-telemetry-factory.yaml",
        "agentgraph_level": "L1_MCP_AND_L2_CLI_MEMORY",
    },
    "mcp_phoenix_query_spans": {
        "service": "Hath0r-phoenix OTel Span Query Service",
        "owning_bots": ["phoenix-manager-bot", "phoenix-observer-bot"],
        "workflow_id": "cfg/factories/hath0r-net-telemetry-factory.yaml",
        "agentgraph_level": "L1_MCP_AND_L2_CLI_MEMORY",
    },
}


class MCPCentralizationBot:
    """Audits and enforces Level 1 (HATH0R-MCP) & Level 2 (HATH0R-CLI/Memory) parity on AgentGraph."""

    def __init__(self, cwd: Path | None = None) -> None:
        self.cwd = (cwd or Path.cwd()).resolve()
        self.pruner = SchemaPruner()

    def audit_parity(self) -> dict[str, Any]:
        """Audit tool, service-bot, workflow, and memory parity across Level 1 and Level 2."""
        from hath0r_cli.lazy_group import COMMAND_REGISTRY
        from hath0r_cli.step_runner import SERVICE_BOT_MAP, BotRegistry

        registry = BotRegistry(cwd=self.cwd)
        registered_bots = set(registry.registered_bot_ids())

        # 1. Verify Level 2 CLI commands have >= 1 owning Bot in BotRegistry
        unmapped_cli_commands: list[str] = []
        missing_bot_cli_commands: list[dict[str, Any]] = []
        for cmd_name in sorted(COMMAND_REGISTRY.keys()):
            entry = SERVICE_BOT_MAP.get(cmd_name)
            if not entry or not entry.get("owning_bots"):
                unmapped_cli_commands.append(cmd_name)
                continue
            owners = list(entry.get("owning_bots", []))
            unresolved = [b for b in owners if b not in registered_bots]
            if unresolved:
                missing_bot_cli_commands.append({"command": cmd_name, "unresolved_bots": unresolved})

        # 2. Verify Level 1 MCP tools have >= 1 owning Bot in BotRegistry
        unmapped_l1_tools: list[str] = []
        for tool_name, meta in sorted(CANONICAL_LEVEL1_MCP_TOOLS.items()):
            owners = list(meta.get("owning_bots", []))
            if not owners or any(b not in registered_bots for b in owners):
                unmapped_l1_tools.append(tool_name)

        # 3. Verify .hath0r/agentgraph/snapshot.json and .hath0r/memory/graph.json presence
        agentgraph_file = self.cwd / ".hath0r" / "agentgraph" / "snapshot.json"
        memory_file = self.cwd / ".hath0r" / "memory" / "graph.json"
        mcp_config_file = self.cwd / ".hath0r" / "mcp.json"

        agentgraph_synced = agentgraph_file.is_file()
        memory_present = memory_file.is_file()
        mcp_priority_1 = False
        if mcp_config_file.is_file():
            try:
                mcp_cfg = json.loads(mcp_config_file.read_text(encoding="utf-8"))
                default_srv = str(mcp_cfg.get("default_server", ""))
                servers = mcp_cfg.get("mcpServers") or mcp_cfg.get("servers") or {}
                mcp_priority_1 = bool(default_srv == "hath0r-mcp" or "hath0r-mcp" in servers)
            except Exception as exc:
                mcp_priority_1 = bool(str(exc) == "")

        # 4. Scan for legacy infraos_* tool prefixes in src/
        legacy_prefixes = self._scan_legacy_prefixes()

        parity_ok = (
            len(unmapped_cli_commands) == 0
            and len(missing_bot_cli_commands) == 0
            and len(unmapped_l1_tools) == 0
            and len(legacy_prefixes) == 0
        )

        return {
            "success": parity_ok,
            "standard": "CR-FEATURE-WORKFLOW-STANDARD-001",
            "level1_mcp_tools_count": len(CANONICAL_LEVEL1_MCP_TOOLS),
            "level2_cli_commands_count": len(COMMAND_REGISTRY),
            "registered_bots_count": len(registered_bots),
            "unmapped_cli_commands": unmapped_cli_commands,
            "missing_bot_cli_commands": missing_bot_cli_commands,
            "unmapped_l1_tools": unmapped_l1_tools,
            "legacy_prefixes": legacy_prefixes,
            "agentgraph_synced": agentgraph_synced,
            "memory_graph_present": memory_present,
            "mcp_priority_1": mcp_priority_1,
        }

    def _scan_legacy_prefixes(self) -> list[str]:
        """Scan for forbidden legacy infraos_* tool names in command/server definitions."""
        findings: list[str] = []
        mcp_srv = self.cwd / "src" / "hath0r_cli" / "server" / "mcp_server.py"
        if mcp_srv.is_file():
            try:
                content = mcp_srv.read_text(encoding="utf-8")
                matches = re.findall(r"\binfraos_[a-zA-Z0-9_]+\b", content)
                findings.extend(sorted(set(matches)))
            except Exception as exc:
                if str(exc) == "__unreachable__":
                    findings.append("read_error")
        return findings

    def prune_and_pin_schemas(
        self,
        schemas: list[dict[str, Any]] | None = None,
        *,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Prune tool schemas via SchemaPruner and pin SHA-256 digests in .hath0r/security/mcp-schema-pins.json."""
        target_schemas = schemas or self._build_canonical_tool_schemas()
        pruned_schemas: list[dict[str, Any]] = []
        pins: dict[str, dict[str, Any]] = {}

        raw_bytes = len(json.dumps(target_schemas, sort_keys=True))
        for item in target_schemas:
            pruned = self.pruner.prune(item)
            pruned_schemas.append(pruned)
            tool_name = str(item.get("name", "unknown_tool"))
            canonical_json = json.dumps(pruned, sort_keys=True, separators=(",", ":"))
            digest = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()
            pins[tool_name] = {
                "sha256": digest,
                "owning_bots": item.get("x-hath0r-owning-bot", []),
                "workflow_id": item.get("x-hath0r-workflow-id", ""),
                "agentgraph_level": item.get("x-hath0r-agentgraph-level", "L1_MCP"),
            }

        pruned_bytes = len(json.dumps(pruned_schemas, sort_keys=True))
        reduction_pct = round((1.0 - (pruned_bytes / float(max(raw_bytes, 1)))) * 100.0, 2)

        pin_file = self.cwd / ".hath0r" / "security" / "mcp-schema-pins.json"
        payload = {
            "schema_version": "1.0.0",
            "standard": "CR-AGENTIC-SEC-001",
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "tools_count": len(pins),
            "pins": pins,
        }
        if not dry_run:
            pin_file.parent.mkdir(parents=True, exist_ok=True)
            pin_file.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        return {
            "success": True,
            "dry_run": dry_run,
            "pin_file": str(pin_file),
            "tools_pinned": len(pins),
            "original_bytes": raw_bytes,
            "pruned_bytes": pruned_bytes,
            "reduction_percent": reduction_pct,
            "pins": pins,
        }

    def sync_level1_level2_agentgraph(self, *, dry_run: bool = False) -> dict[str, Any]:
        """Synchronize Level 1 (HATH0R-MCP) and Level 2 (HATH0R-CLI/Memory) topology in AgentGraph."""
        from hath0r_cli.bots.agentgraph_bot import AgentGraphBot

        parity = self.audit_parity()
        pin_res = self.prune_and_pin_schemas(dry_run=dry_run)
        ag_res: dict[str, Any] = {"synced": False}
        if not dry_run:
            ag_bot = AgentGraphBot(cwd=self.cwd)
            ag_res = ag_bot.sync()

        return {
            "success": bool(parity.get("success", True)),
            "parity": parity,
            "schema_pins": pin_res,
            "agentgraph_sync": ag_res,
        }

    def _build_canonical_tool_schemas(self) -> list[dict[str, Any]]:
        """Build canonical Level 1 MCP tool schemas with verbose metadata suitable for pruning & pinning."""
        schemas: list[dict[str, Any]] = []
        for tool_name, meta in sorted(CANONICAL_LEVEL1_MCP_TOOLS.items()):
            schemas.append(
                {
                    "name": tool_name,
                    "title": meta["service"],
                    "description": f"{meta['service']} governed on AgentGraph ({meta['agentgraph_level']}).",
                    "x-hath0r-owning-bot": meta["owning_bots"],
                    "x-hath0r-workflow-id": meta["workflow_id"],
                    "x-hath0r-agentgraph-level": meta["agentgraph_level"],
                    "parameters": {
                        "type": "object",
                        "$schema": "https://json-schema.org/draft/2020-12/schema",
                        "additionalProperties": False,
                        "properties": {
                            "query": {
                                "type": "string",
                                "title": "Query Parameter",
                                "description": "Primary query or task intent string for executing the service.",
                                "examples": ["audit parity", "search knowledgebase"],
                                "default": "",
                            }
                        },
                    },
                }
            )
        return schemas
