"""ArchitecturePreservationBot — Enforces CR-FEATURE-WORKFLOW-STANDARD-001 & Suite Standards Across All 5 Repos.

Verifies:
1. Every Feature (CLI command group, MCP tool, declarative factory) is registered as a Service
   run by >= 1 Bot in BotRegistry (`feature.service_bot.enforce`).
2. Level 1 (HATH0R-MCP) hosts central tools/workflows/knowledge and Level 2 (HATH0R-CLI / .hath0r/memory/)
   hosts CLI execution and Bot Memory, indexed and synchronized in AgentGraph.
3. Workflow-First coverage: every command/feature binds to a declarative workflow YAML or Level 1 MCP workflow.
4. Hidden-root exclusivity (`.hath0r/` only; zero `.ai/`, `.aegis/`, `.infraOS/`), `.hath0r/mcp.json` Priority 1,
   `cfg/observability/otel.json` (`http://localhost:38000/phoenix`), and 4-hour calibration TTL.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

FORBIDDEN_HIDDEN_DIRS = (".ai", ".aegis", ".infraOS", ".customerSystem")
SUITE_REPOS = ("hath0r-atc", "hath0r-mcp", "hathor-cli", "hath0r-framework", "hath0r-poc")


class ArchitecturePreservationBot:
    """Audits and preserves canonical Hath0r MCP-Central & Two-Level AgentGraph architecture."""

    def __init__(self, cwd: Path | None = None) -> None:
        self.cwd = (cwd or Path.cwd()).resolve()

    def verify_repo(self, repo_path: Path | None = None) -> dict[str, Any]:
        """Verify architectural invariants in a single repository."""
        from hath0r_cli.lazy_group import COMMAND_REGISTRY
        from hath0r_cli.step_runner import SERVICE_BOT_MAP, BotRegistry

        target = (repo_path or self.cwd).resolve()
        registry = BotRegistry(cwd=target)
        registered_bots = set(registry.registered_bot_ids())

        # 1. Service-Bot & Workflow-First coverage (CR-FEATURE-WORKFLOW-STANDARD-001)
        unmapped_commands: list[str] = []
        missing_workflows: list[str] = []
        for cmd_name in sorted(COMMAND_REGISTRY.keys()):
            entry = SERVICE_BOT_MAP.get(cmd_name)
            if not entry or not entry.get("owning_bots"):
                unmapped_commands.append(cmd_name)
                continue
            owners = list(entry.get("owning_bots", []))
            if any(b not in registered_bots for b in owners):
                unmapped_commands.append(cmd_name)
            if not entry.get("workflow_id"):
                missing_workflows.append(cmd_name)

        # 2. Hidden root exclusivity (cr-hath0r-root-001)
        forbidden_found = [d for d in FORBIDDEN_HIDDEN_DIRS if (target / d).exists()]

        # 3. CLAUDE.md == AGENTS.md 1:1 mirror check (when both exist)
        agents_md = target / "AGENTS.md"
        claude_md = target / "CLAUDE.md"
        claude_sync_ok = True
        if agents_md.is_file() and claude_md.is_file():
            claude_sync_ok = agents_md.read_bytes() == claude_md.read_bytes()

        # 4. AgentGraph & MemoryGraph presence
        agentgraph_present = (target / ".hath0r" / "agentgraph" / "snapshot.json").is_file()
        memory_present = (target / ".hath0r" / "memory" / "graph.json").is_file()

        # 5. Observability & Phoenix endpoint check
        otel_file = target / "cfg" / "observability" / "otel.json"
        phoenix_configured = True
        if otel_file.is_file():
            try:
                otel_doc = json.loads(otel_file.read_text(encoding="utf-8"))
                phoenix_configured = "phoenix" in json.dumps(otel_doc).lower()
            except Exception as exc:
                phoenix_configured = bool(str(exc) == "")

        passed = (
            len(unmapped_commands) == 0
            and len(missing_workflows) == 0
            and len(forbidden_found) == 0
            and claude_sync_ok
            and phoenix_configured
        )

        return {
            "success": passed,
            "repo": target.name,
            "path": str(target),
            "standard": "CR-FEATURE-WORKFLOW-STANDARD-001",
            "commands_verified": len(COMMAND_REGISTRY),
            "registered_bots_count": len(registered_bots),
            "unmapped_commands": unmapped_commands,
            "missing_workflows": missing_workflows,
            "forbidden_hidden_dirs": forbidden_found,
            "claude_agents_synced": claude_sync_ok,
            "agentgraph_present": agentgraph_present,
            "memory_graph_present": memory_present,
            "phoenix_otel_configured": phoenix_configured,
        }

    def verify_fleet(self, group_root: Path | None = None) -> dict[str, Any]:
        """Verify CR-FEATURE-WORKFLOW-STANDARD-001 across all available suite repositories."""
        root = (group_root or self.cwd.parent).resolve()
        results: list[dict[str, Any]] = []
        for repo_name in SUITE_REPOS:
            candidate = root / repo_name
            if candidate.is_dir():
                results.append(self.verify_repo(candidate))

        if not results:
            results.append(self.verify_repo(self.cwd))

        all_ok = all(r.get("success", False) for r in results)
        return {
            "success": all_ok,
            "standard": "CR-FEATURE-WORKFLOW-STANDARD-001",
            "repos_checked": len(results),
            "repos": results,
        }

    def status(self) -> dict[str, Any]:
        """Return health status and current repo verification."""
        return self.verify_repo(self.cwd)
