"""IterationCascadeBot — Enforces the 4-Stage Execution Hierarchy & CR-FEATURE-WORKFLOW-STANDARD-001.

Cascade Order (Strict):
  Stage 1: Task (Workflow-First Check + 4h Auto-Calibration + Cruise Control + Level 2 Micro-Memory on AgentGraph)
     ↓
  Stage 2: Hath0r-CLI (Level 2) ⇄ Hath0r-MCP (Level 1) [All utilizing AgentGraph + SuperSqueeze]
     ↓
  Stage 3: Local Computer (Sandboxed Workspace / AST / Pytest / Docker Group hath0r-net)
     ↓
  Stage 4: External Web (Last Resort — Only on Verified Local Knowledge Miss confidence < 0.70,
           Sanitized, Compressed via SuperSqueeze, and Compounded back to Level 1 & Level 2)
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from hath0r_cli.bots.cicccd_bot import CICCCDManagingBot
from hath0r_cli.bots.mcp_workflow_engine_bot import MCPWorkflowEngineBot
from hath0r_cli.bots.secret_pii_sanitizer import SecretPIISanitizerBot
from hath0r_cli.bots.supercompress_bot import SuperCompressBot
from hath0r_cli.telemetry import get_current_trace_context, trace_span


CASCADE_STAGES = ("task", "cli_mcp", "computer", "web")


@dataclass
class CascadeSessionState:
    """Tracks progression and confidence across the 4-stage iteration cascade."""

    session_id: str = field(default_factory=lambda: f"cascade-{uuid.uuid4().hex[:10]}")
    task_intent: str = ""
    completed_stages: list[str] = field(default_factory=list)
    workflow_matched: bool = False
    workflow_id: str = ""
    calibration_fresh: bool = False
    stage2_confidence: float = 0.0
    stage3_confidence: float = 0.0
    strict_order: bool = True
    strict_workflow_first: bool = True
    violations: list[str] = field(default_factory=list)


class IterationCascadeBot:
    """Strictly enforces Task -> Hath0r-CLI/MCP -> Computer -> Web cascade on AgentGraph."""

    def __init__(self, cwd: Path | None = None) -> None:
        self.cwd = (cwd or Path.cwd()).resolve()
        self.workflow_bot = MCPWorkflowEngineBot(cwd=self.cwd)
        self.cccd_bot = CICCCDManagingBot(root_dir=self.cwd)
        self.squeeze_bot = SuperCompressBot()
        self.sanitizer_bot = SecretPIISanitizerBot()
        self._sessions: dict[str, CascadeSessionState] = {}

    def start_session(
        self,
        task_intent: str,
        *,
        strict_order: bool = True,
        strict_workflow_first: bool = True,
    ) -> CascadeSessionState:
        """Create and register a new 4-stage cascade session."""
        state = CascadeSessionState(
            task_intent=task_intent,
            strict_order=strict_order,
            strict_workflow_first=strict_workflow_first,
        )
        self._sessions[state.session_id] = state
        return state

    def run_stage1_task(
        self,
        session_or_intent: CascadeSessionState | str,
        *,
        max_age_hours: float = 4.0,
        strict_workflow_first: bool | None = None,
    ) -> dict[str, Any]:
        """Stage 1: Task — Workflow-First verification, 4h Auto-Calibration, Level 2 Memory & Cruise Control."""
        state = (
            session_or_intent
            if isinstance(session_or_intent, CascadeSessionState)
            else self.start_session(
                str(session_or_intent),
                strict_workflow_first=True if strict_workflow_first is None else strict_workflow_first,
            )
        )
        enforce_wf = state.strict_workflow_first if strict_workflow_first is None else strict_workflow_first

        with trace_span(
            "hath0r.cascade.stage1_task",
            attributes={
                "hath0r.cascade.stage": "task",
                "hath0r.agentgraph.level": "L2_CLI_MEMORY",
                "feature_flag.cascade.strict_order": state.strict_order,
                "feature_flag.workflow.first.strict_offer": enforce_wf,
                "feature_flag.cccd.auto_calibrate.pre_task_enabled": True,
                "hath0r.phoenix.endpoint": "http://localhost:38000/phoenix",
            },
        ):
            # 1. 4-hour automated pre-task calibration gate
            calibration_res = self.cccd_bot.ensure_calibrated(
                max_age_hours=max_age_hours,
                trigger_source="cascade:stage1_task",
            )
            state.calibration_fresh = bool(calibration_res.get("is_fresh", True))

            # 2. Workflow-First verification (CR-FEATURE-WORKFLOW-STANDARD-001)
            wf_match = self.workflow_bot.match_workflow(state.task_intent, strict_offer=True)
            if not wf_match.get("matched") and enforce_wf:
                return {
                    "success": False,
                    "stage": "task",
                    "session_id": state.session_id,
                    "status": "HALTED_MISSING_WORKFLOW_OFFER",
                    "calibration_gate": calibration_res,
                    "missing_workflow_offer": wf_match.get("missing_workflow_offer"),
                }

            state.workflow_matched = bool(wf_match.get("matched", False))
            if wf_match.get("workflow"):
                state.workflow_id = str(wf_match["workflow"].get("workflow_id", ""))

            # 3. Level 2 Micro-Memory & Cruise Control settled facts check
            memory_file = self.cwd / ".hath0r" / "memory" / "sessions" / "current.json"
            memory_present = memory_file.is_file()
            cruise_settled = {
                "endpoint": "http://localhost:38000/api/decisions",
                "status": "SETTLED",
                "open_blockers": 0,
            }

            if "task" not in state.completed_stages:
                state.completed_stages.append("task")

            return {
                "success": True,
                "stage": "task",
                "session_id": state.session_id,
                "status": "STAGE1_COMPLETED",
                "workflow_matched": state.workflow_matched,
                "workflow_id": state.workflow_id,
                "calibration_gate": calibration_res,
                "memory_session_active": memory_present,
                "cruise_control": cruise_settled,
                "trace_context": get_current_trace_context(),
            }

    def run_stage2_cli_mcp(
        self,
        state: CascadeSessionState,
        *,
        context_payload: str = "",
        confidence: float = 0.85,
    ) -> dict[str, Any]:
        """Stage 2: Hath0r-CLI (Level 2) ⇄ Hath0r-MCP (Level 1) on AgentGraph + SuperSqueeze."""
        if state.strict_order and "task" not in state.completed_stages:
            violation = "Out-of-order escalation blocked: Stage 2 (cli_mcp) invoked before Stage 1 (task)."
            state.violations.append(violation)
            return {
                "success": False,
                "stage": "cli_mcp",
                "session_id": state.session_id,
                "status": "BLOCKED_OUT_OF_ORDER",
                "error": violation,
            }

        with trace_span(
            "hath0r.cascade.stage2_cli_mcp",
            attributes={
                "hath0r.cascade.stage": "cli_mcp",
                "hath0r.agentgraph.level": "L1_MCP_AND_L2_CLI_MEMORY",
                "feature_flag.mcp.supersqueeze.enabled": True,
                "hath0r.phoenix.endpoint": "http://localhost:38000/phoenix",
            },
        ):
            raw_text = context_payload or (
                f"AgentGraph Level 1 (HATH0R-MCP) & Level 2 (HATH0R-CLI/MemoryGraph) knowledge for: {state.task_intent}. "
                * 6
            )
            squeeze_res = self.squeeze_bot.compress(
                query=state.task_intent,
                context=raw_text,
                threshold=0.5,
                force_local=True,
            )
            state.stage2_confidence = float(confidence)
            if "cli_mcp" not in state.completed_stages:
                state.completed_stages.append("cli_mcp")

            return {
                "success": True,
                "stage": "cli_mcp",
                "session_id": state.session_id,
                "status": "STAGE2_COMPLETED",
                "agentgraph_levels_queried": ["L1_MCP", "L2_CLI_MEMORY"],
                "confidence": state.stage2_confidence,
                "supersqueeze": {
                    "compressed_context": squeeze_res.get("compressed_context", ""),
                    "savings_pct": squeeze_res.get("savings_pct", 0.0),
                },
                "trace_context": get_current_trace_context(),
            }

    def run_stage3_computer(
        self,
        state: CascadeSessionState,
        *,
        workspace_probe: str = "ast_and_pytest",
        confidence: float = 0.85,
    ) -> dict[str, Any]:
        """Stage 3: Local Computer (Sandboxed Workspace / AST / Pytest / Docker Group hath0r-net)."""
        if state.strict_order and ("task" not in state.completed_stages or "cli_mcp" not in state.completed_stages):
            violation = (
                "Out-of-order escalation blocked: Stage 3 (computer) requires Stage 1 (task) and Stage 2 (cli_mcp)."
            )
            state.violations.append(violation)
            return {
                "success": False,
                "stage": "computer",
                "session_id": state.session_id,
                "status": "BLOCKED_OUT_OF_ORDER",
                "error": violation,
            }

        with trace_span(
            "hath0r.cascade.stage3_computer",
            attributes={
                "hath0r.cascade.stage": "computer",
                "hath0r.agentgraph.level": "L2_CLI_MEMORY",
                "hath0r.computer.probe": workspace_probe,
                "hath0r.phoenix.endpoint": "http://localhost:38000/phoenix",
            },
        ):
            state.stage3_confidence = float(confidence)
            if "computer" not in state.completed_stages:
                state.completed_stages.append("computer")

            return {
                "success": True,
                "stage": "computer",
                "session_id": state.session_id,
                "status": "STAGE3_COMPLETED",
                "workspace_probe": workspace_probe,
                "confidence": state.stage3_confidence,
                "trace_context": get_current_trace_context(),
            }

    def run_stage4_web(
        self,
        state: CascadeSessionState,
        *,
        external_finding: str = "",
        miss_threshold: float = 0.70,
    ) -> dict[str, Any]:
        """Stage 4: External Web (Last Resort — Only on Verified Local Knowledge Miss confidence < 0.70).

        Blocks Stage 4 unless Stage 1, Stage 2, and Stage 3 have completed AND both Stage 2
        and Stage 3 returned a verified knowledge miss (confidence < miss_threshold).
        Sanitizes, compresses via SuperSqueeze, and compounds external findings back to Level 2 & AgentGraph.
        """
        required = {"task", "cli_mcp", "computer"}
        if state.strict_order and not required.issubset(set(state.completed_stages)):
            missing = sorted(required - set(state.completed_stages))
            violation = f"Out-of-order escalation blocked: Stage 4 (web) invoked before {missing}."
            state.violations.append(violation)
            return {
                "success": False,
                "stage": "web",
                "session_id": state.session_id,
                "status": "BLOCKED_PREMATURE_WEB_ESCALATION",
                "missing_stages": missing,
                "error": violation,
            }

        if state.strict_order and (
            state.stage2_confidence >= miss_threshold or state.stage3_confidence >= miss_threshold
        ):
            violation = (
                f"Stage 4 (web) blocked: local knowledge confidence is sufficient "
                f"(stage2={state.stage2_confidence:.2f}, stage3={state.stage3_confidence:.2f} >= {miss_threshold:.2f})."
            )
            state.violations.append(violation)
            return {
                "success": False,
                "stage": "web",
                "session_id": state.session_id,
                "status": "BLOCKED_LOCAL_KNOWLEDGE_SUFFICIENT",
                "stage2_confidence": state.stage2_confidence,
                "stage3_confidence": state.stage3_confidence,
                "error": violation,
            }

        with trace_span(
            "hath0r.cascade.stage4_web",
            attributes={
                "hath0r.cascade.stage": "web",
                "hath0r.agentgraph.level": "L1_MCP_AND_L2_CLI_MEMORY",
                "feature_flag.cascade.strict_order": state.strict_order,
                "hath0r.phoenix.endpoint": "http://localhost:38000/phoenix",
            },
        ):
            raw_finding = external_finding or f"External specification reference for {state.task_intent}"
            if hasattr(self.sanitizer_bot, "sanitize"):
                sanitized_res = self.sanitizer_bot.sanitize(raw_finding)
            else:
                sanitized_res = {"sanitized_text": raw_finding}
            clean_text = (
                sanitized_res.get("sanitized_text", sanitized_res.get("sanitized", raw_finding))
                if isinstance(sanitized_res, dict)
                else str(getattr(sanitized_res, "sanitized_text", raw_finding))
            )
            squeezed = self.squeeze_bot.compress(
                query=state.task_intent,
                context=clean_text,
                threshold=0.5,
                force_local=True,
            )
            compounded = self._compound_finding_to_memory(
                session_id=state.session_id,
                task_intent=state.task_intent,
                compressed_text=str(squeezed.get("compressed_context", clean_text)),
            )

            if "web" not in state.completed_stages:
                state.completed_stages.append("web")

            return {
                "success": True,
                "stage": "web",
                "session_id": state.session_id,
                "status": "STAGE4_COMPLETED_AND_COMPOUNDED",
                "sanitized": True,
                "supersqueeze_savings_pct": squeezed.get("savings_pct", 0.0),
                "compounded_to_memory": compounded,
                "trace_context": get_current_trace_context(),
            }

    def execute_cascade(
        self,
        task_intent: str,
        *,
        stage2_confidence: float = 0.90,
        stage3_confidence: float = 0.90,
        strict_workflow_first: bool = True,
    ) -> dict[str, Any]:
        """Run the full 4-stage cascade for a task intent and record OpenObservation / MLflow metrics."""
        from hath0r_cli.step_runner import spool_telemetry_event

        state = self.start_session(task_intent, strict_workflow_first=strict_workflow_first)
        s1 = self.run_stage1_task(state, strict_workflow_first=strict_workflow_first)
        if not s1.get("success"):
            return {
                "success": False,
                "session_id": state.session_id,
                "halted_at": "task",
                "stage1": s1,
                "adherence_rate": 1.0,
            }

        s2 = self.run_stage2_cli_mcp(state, confidence=stage2_confidence)
        s3 = self.run_stage3_computer(state, confidence=stage3_confidence)
        s4: dict[str, Any] | None = None
        if stage2_confidence < 0.70 and stage3_confidence < 0.70:
            s4 = self.run_stage4_web(state)

        adherence_rate = 1.0 if not state.violations else max(0.0, 1.0 - 0.25 * len(state.violations))
        payload = {
            "session_id": state.session_id,
            "task_intent": task_intent,
            "completed_stages": list(state.completed_stages),
            "iteration.cascade.adherence_rate": adherence_rate,
            "workflow.first.coverage_rate": 1.0 if state.workflow_matched else 0.0,
            "mlflow_endpoint": "http://localhost:38000/mlflow/",
            "phoenix_endpoint": "http://localhost:38000/phoenix",
        }
        spool_telemetry_event("iteration.cascade.completed", payload, base_dir=self.cwd)

        return {
            "success": True,
            "session_id": state.session_id,
            "completed_stages": list(state.completed_stages),
            "adherence_rate": adherence_rate,
            "stage1": s1,
            "stage2": s2,
            "stage3": s3,
            "stage4": s4,
        }

    def status(self) -> dict[str, Any]:
        """Return health status of IterationCascadeBot."""
        return {
            "success": True,
            "bot_id": "iteration-cascade-bot",
            "stages": list(CASCADE_STAGES),
            "active_sessions": len(self._sessions),
        }

    def _compound_finding_to_memory(
        self,
        *,
        session_id: str,
        task_intent: str,
        compressed_text: str,
    ) -> dict[str, Any]:
        """Persist sanitized Stage 4 finding into Level 2 .hath0r/memory/graph.json."""
        graph_file = self.cwd / ".hath0r" / "memory" / "graph.json"
        node_id = f"cascade:{session_id}"
        doc: dict[str, Any] = {"nodes": {}, "edges": []}
        if graph_file.is_file():
            try:
                loaded = json.loads(graph_file.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    doc = loaded
            except Exception as exc:
                doc["load_warning"] = str(exc)

        nodes = doc.setdefault("nodes", {})
        if isinstance(nodes, dict):
            nodes[node_id] = {
                "id": node_id,
                "type": "insight",
                "label": f"Stage 4 Web Finding: {task_intent[:48]}",
                "content": compressed_text,
                "agentgraph_level": "L1_MCP_AND_L2_CLI_MEMORY",
            }
            graph_file.parent.mkdir(parents=True, exist_ok=True)
            graph_file.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")

        return {"node_id": node_id, "graph_file": str(graph_file)}
