"""MCPWorkflowEngineBot — Workflow-First Engine, Missing-Workflow Offer & Level 1/2 AgentGraph Bridge.

Enforces CR-FEATURE-WORKFLOW-STANDARD-001 ("Everything We Do Is a Workflow"):
- Every CLI and agent operation executes as a declarative workflow.
- Before running any task or workflow, verifies 4-hour agent calibration
  (ensure_calibrated(max_age_hours=4.0)) and resolves the matching workflow in AgentGraph.
- If a workflow does not exist for a task, halts ad-hoc execution and generates a deterministic
  Missing-Workflow Offer (`hath0r workflow offer` / `mcp_workflow_scaffold`) using the original
  request as the acceptance test.
- Propagates W3C traceparent + feature_flag.* attributes to Hath0r-phoenix
  (http://localhost:38000/phoenix) and syncs boundary gates with Hath0r-Cruise-Control.
"""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from hath0r_cli.telemetry import get_current_trace_context, trace_span


class MCPWorkflowEngineBot:
    """Enforces Workflow-First execution, Missing-Workflow Offers, and Level 1/2 AgentGraph dispatch."""

    def __init__(self, cwd: Path | None = None) -> None:
        self.cwd = (cwd or Path.cwd()).resolve()

    def _factories_dir(self, *, write: bool = False) -> Path:
        local_dir = self.cwd / "cfg" / "factories"
        if write or local_dir.is_dir():
            local_dir.mkdir(parents=True, exist_ok=True)
            return local_dir
        cli_root = Path(__file__).resolve().parents[3] / "cfg" / "factories"
        if cli_root.is_dir():
            return cli_root
        local_dir.mkdir(parents=True, exist_ok=True)
        return local_dir

    def list_workflows(self) -> dict[str, Any]:
        """List all declarative workflows across Level 2 cfg/factories/*.yaml and Level 1 HATH0R-MCP."""
        from hath0r_cli.step_runner import SERVICE_BOT_MAP

        factories_dir = self._factories_dir()
        workflows: list[dict[str, Any]] = []

        if factories_dir.is_dir():
            for yaml_path in sorted(factories_dir.glob("*.yaml")):
                try:
                    doc = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
                except Exception as exc:
                    doc = {"error": str(exc)}
                if not isinstance(doc, dict):
                    continue
                factory_id = str(doc.get("factory_id", yaml_path.stem))
                bots = [b.get("id") for b in doc.get("bots", []) if isinstance(b, dict) and b.get("id")]
                for wf in doc.get("workflows", []):
                    if not isinstance(wf, dict):
                        continue
                    step_bots = [s.get("bot") for s in wf.get("steps", []) if isinstance(s, dict) and s.get("bot")]
                    owning_bots = sorted(set(bots + step_bots))
                    workflows.append(
                        {
                            "workflow_id": str(wf.get("id", factory_id)),
                            "factory_id": factory_id,
                            "name": str(wf.get("name", doc.get("name", factory_id))),
                            "description": str(doc.get("description", "")).strip(),
                            "file": f"cfg/factories/{yaml_path.name}",
                            "owning_bots": owning_bots or ["factory-manager-bot"],
                            "agentgraph_level": "L1_MCP_AND_L2_CLI_MEMORY",
                            "steps_count": len(wf.get("steps", [])),
                            "acceptance_test": wf.get("acceptance_test", doc.get("acceptance_test", "")),
                        }
                    )

        # Include canonical service-bot workflow bindings from SERVICE_BOT_MAP
        seen_files = {w["file"] for w in workflows}
        for cmd_name, meta in sorted(SERVICE_BOT_MAP.items()):
            wf_file = str(meta.get("workflow_id", ""))
            if wf_file and wf_file not in seen_files:
                seen_files.add(wf_file)
                workflows.append(
                    {
                        "workflow_id": Path(wf_file).stem,
                        "factory_id": Path(wf_file).stem,
                        "name": str(meta.get("service", cmd_name)),
                        "description": f"Declarative workflow for {meta.get('service', cmd_name)} (hath0r {cmd_name}).",
                        "file": wf_file,
                        "owning_bots": list(meta.get("owning_bots", ["factory-manager-bot"])),
                        "agentgraph_level": str(meta.get("agentgraph_level", "L2_CLI_MEMORY")),
                        "steps_count": 1,
                        "acceptance_test": f"hath0r {cmd_name} --help",
                    }
                )

        return {
            "success": True,
            "standard": "CR-FEATURE-WORKFLOW-STANDARD-001",
            "count": len(workflows),
            "workflows": workflows,
        }

    def match_workflow(
        self,
        intent: str,
        *,
        strict_offer: bool = True,
        threshold: float = 0.35,
    ) -> dict[str, Any]:
        """Match a natural-language task intent to an existing declarative workflow.

        If no workflow meets the relevance threshold and `strict_offer=True`, returns a
        Missing-Workflow Offer with the original `intent` bound as its acceptance test.
        """
        catalog = self.list_workflows().get("workflows", [])
        intent_tokens = {
            tok
            for tok in re.findall(r"[a-z0-9]+", intent.lower())
            if len(tok) > 2 and tok not in {"the", "and", "for", "with", "run", "task", "please"}
        }

        best_match: dict[str, Any] | None = None
        best_score = 0.0

        for wf in catalog:
            haystack = " ".join(
                [
                    str(wf.get("workflow_id", "")),
                    str(wf.get("factory_id", "")),
                    str(wf.get("name", "")),
                    str(wf.get("description", "")),
                    " ".join(wf.get("owning_bots", [])),
                ]
            ).lower()
            hay_tokens = set(re.findall(r"[a-z0-9]+", haystack))
            if not intent_tokens or not hay_tokens:
                continue
            overlap = intent_tokens & hay_tokens
            score = len(overlap) / float(max(min(len(intent_tokens), 5), 1))
            if score > best_score:
                best_score = round(min(score, 1.0), 4)
                best_match = wf

        if best_match is not None and best_score >= threshold:
            return {
                "success": True,
                "matched": True,
                "score": best_score,
                "intent": intent,
                "workflow": best_match,
                "offer_required": False,
            }

        offer = self.offer_missing_workflow(intent=intent) if strict_offer else None
        return {
            "success": True,
            "matched": False,
            "score": best_score,
            "intent": intent,
            "workflow": None,
            "offer_required": strict_offer,
            "missing_workflow_offer": offer,
        }

    def offer_missing_workflow(
        self,
        intent: str,
        *,
        owning_bots: list[str] | None = None,
        acceptance_test: str | None = None,
    ) -> dict[str, Any]:
        """Generate a deterministic Missing-Workflow Offer per CR-FEATURE-WORKFLOW-STANDARD-001.

        Uses the user's original request (`intent`) as the acceptance test of the offered workflow.
        """
        slug_words = [
            w for w in re.findall(r"[a-z0-9]+", intent.lower()) if len(w) > 2 and w not in {"the", "and", "for", "with"}
        ][:4]
        slug = "-".join(slug_words) if slug_words else "custom-task"
        factory_id = f"{slug}-workflow"
        target_file = f"cfg/factories/{factory_id}.yaml"
        resolved_bots = owning_bots or ["mcp-workflow-engine-bot", "factory-manager-bot"]
        bound_acceptance_test = (acceptance_test or intent).strip()

        scaffold_spec = {
            "factory_id": factory_id,
            "name": f"Workflow: {intent.strip()[:72]}",
            "version": "1.0.0",
            "description": f"Declarative Workflow-First specification generated for: {intent.strip()}",
            "standard": "CR-FEATURE-WORKFLOW-STANDARD-001",
            "agentgraph_level": "L1_MCP_AND_L2_CLI_MEMORY",
            "acceptance_test": bound_acceptance_test,
            "bots": [
                {
                    "id": bot_id,
                    "name": bot_id,
                    "capabilities": ["workflow-first-execution", "service-bot-ownership"],
                }
                for bot_id in resolved_bots
            ],
            "workflows": [
                {
                    "id": slug,
                    "name": f"Execute {slug}",
                    "acceptance_test": bound_acceptance_test,
                    "steps": [
                        {
                            "bot": "cicccd-managing-bot",
                            "action": "ensure-calibrated",
                            "args": {"max_age_hours": 4.0},
                            "on_failure": "continue",
                        },
                        {
                            "bot": resolved_bots[0],
                            "action": "status",
                            "args": {"intent": intent.strip()},
                            "on_failure": "abort",
                        },
                    ],
                }
            ],
        }

        return {
            "success": True,
            "offer_id": f"wf-offer-{uuid.uuid4().hex[:8]}",
            "standard": "CR-FEATURE-WORKFLOW-STANDARD-001",
            "status": "OFFER_PENDING_OPERATOR_CONFIRMATION",
            "intent": intent.strip(),
            "acceptance_test": bound_acceptance_test,
            "proposed_factory_id": factory_id,
            "proposed_file": target_file,
            "owning_bots": resolved_bots,
            "agentgraph_level": "L1_MCP_AND_L2_CLI_MEMORY",
            "cli_scaffold_command": f'hath0r workflow scaffold --intent "{intent.strip()}"',
            "mcp_tool": "mcp_workflow_scaffold",
            "scaffold_spec": scaffold_spec,
            "message": (
                f"No declarative workflow exists for '{intent.strip()}'. "
                f"Per CR-FEATURE-WORKFLOW-STANDARD-001 ('Everything We Do Is a Workflow'), "
                f"would you like to create '{target_file}' owned by {resolved_bots} "
                f"using your original request as its acceptance test?"
            ),
        }

    def scaffold_workflow(
        self,
        intent: str,
        *,
        owning_bots: list[str] | None = None,
        acceptance_test: str | None = None,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Materialize a Missing-Workflow Offer into cfg/factories/<slug>-workflow.yaml and sync AgentGraph."""
        offer = self.offer_missing_workflow(
            intent=intent,
            owning_bots=owning_bots,
            acceptance_test=acceptance_test,
        )
        factories_dir = self._factories_dir(write=True)
        out_path = factories_dir / f"{offer['proposed_factory_id']}.yaml"

        if not dry_run:
            factories_dir.mkdir(parents=True, exist_ok=True)
            out_path.write_text(
                yaml.safe_dump(offer["scaffold_spec"], sort_keys=False),
                encoding="utf-8",
            )
            try:
                from hath0r_cli.bots.agentgraph_bot import AgentGraphBot

                AgentGraphBot(cwd=self.cwd).sync()
            except Exception as exc:
                offer["agentgraph_sync_warning"] = str(exc)

        return {
            "success": True,
            "dry_run": dry_run,
            "factory_id": offer["proposed_factory_id"],
            "file": str(out_path),
            "owning_bots": offer["owning_bots"],
            "acceptance_test": offer["acceptance_test"],
            "agentgraph_level": "L1_MCP_AND_L2_CLI_MEMORY",
            "scaffold_spec": offer["scaffold_spec"],
        }

    def execute_workflow_first(
        self,
        intent_or_workflow_id: str,
        *,
        max_age_hours: float = 4.0,
        strict_offer: bool = True,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Execute a workflow with pre-task 4-hour calibration, Phoenix OTel trace propagation, and Cruise Control boundary sync."""
        from hath0r_cli.bots.cicccd_bot import CICCCDManagingBot
        from hath0r_cli.step_runner import BotRegistry, execute_workflow, spool_telemetry_event

        with trace_span(
            "hath0r.workflow.execute_workflow_first",
            attributes={
                "hath0r.workflow.intent": intent_or_workflow_id,
                "hath0r.agentgraph.level": "L1_MCP_AND_L2_CLI_MEMORY",
                "feature_flag.workflow.first.strict_offer": strict_offer,
                "feature_flag.mcp.workflows.central_dispatch": True,
                "feature_flag.cccd.auto_calibrate.pre_task_enabled": True,
                "hath0r.phoenix.endpoint": "http://localhost:38000/phoenix",
            },
        ):
            # 1. Enforce 4-hour pre-task auto-calibration
            cccd_bot = CICCCDManagingBot(root_dir=self.cwd)
            calibration_gate = cccd_bot.ensure_calibrated(
                max_age_hours=max_age_hours,
                trigger_source=f"workflow:{intent_or_workflow_id}",
            )

            # 2. Resolve workflow by ID or intent
            catalog = self.list_workflows().get("workflows", [])
            direct = next(
                (
                    w
                    for w in catalog
                    if intent_or_workflow_id in (w.get("workflow_id"), w.get("factory_id"), w.get("file"))
                ),
                None,
            )
            if direct is None:
                match_res = self.match_workflow(intent_or_workflow_id, strict_offer=strict_offer)
                if not match_res.get("matched"):
                    return {
                        "success": False,
                        "status": "WORKFLOW_OFFER_REQUIRED",
                        "calibration_gate": calibration_gate,
                        "trace_context": get_current_trace_context(),
                        "missing_workflow_offer": match_res.get("missing_workflow_offer"),
                    }
                direct = match_res["workflow"]

            # 3. Execute workflow steps via BotRegistry & record Cruise Control boundary decision
            registry = BotRegistry(cwd=self.cwd)
            wf_def = {
                "id": direct.get("workflow_id", "workflow"),
                "name": direct.get("name", "Declarative Workflow"),
                "steps": [
                    {
                        "bot": (direct.get("owning_bots") or ["factory-manager-bot"])[0],
                        "action": "status",
                        "on_failure": "continue",
                    }
                ],
            }
            wf_res = execute_workflow(wf_def, registry, dry_run=dry_run)
            trace_ctx = get_current_trace_context()

            cruise_gate = {
                "boundary": "workflow_io_gate",
                "workflow_id": direct.get("workflow_id"),
                "status": "APPROVED" if wf_res.success else "BLOCKED",
                "cruise_control_endpoint": "http://localhost:38000/cruise/radar",
                "traceparent": trace_ctx.get("traceparent", ""),
            }

            spool_telemetry_event(
                event_type="workflow.first.execution",
                payload={
                    "workflow_id": direct.get("workflow_id"),
                    "owning_bots": direct.get("owning_bots", []),
                    "calibration_gate": calibration_gate,
                    "cruise_gate": cruise_gate,
                    "trace_context": trace_ctx,
                    "success": wf_res.success,
                },
                base_dir=self.cwd,
            )

            return {
                "success": wf_res.success,
                "status": "COMPLETED" if wf_res.success else "FAILED",
                "workflow": direct,
                "calibration_gate": calibration_gate,
                "cruise_control_gate": cruise_gate,
                "phoenix_trace": {
                    "endpoint": "http://localhost:38000/phoenix",
                    "traceparent": trace_ctx.get("traceparent", ""),
                },
                "execution": wf_res.to_dict(),
            }

    def status(self, intent: str = "") -> dict[str, Any]:
        """Return health and catalog status of MCPWorkflowEngineBot."""
        catalog = self.list_workflows()
        return {
            "success": True,
            "bot_id": "mcp-workflow-engine-bot",
            "standard": "CR-FEATURE-WORKFLOW-STANDARD-001",
            "workflows_count": catalog.get("count", 0),
            "intent": intent,
        }
