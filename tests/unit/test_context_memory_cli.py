"""Tests for context query and memory search CLI commands."""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from hath0r_cli.bots.context_manager import ContextManagerBot
from hath0r_cli.bots.memory_manager import MemoryManagerBot
from hath0r_cli.cli import main


def test_context_manager_bot_query_empty(tmp_path: Path) -> None:
    bot = ContextManagerBot(cwd=tmp_path)
    res = bot.query_context()
    assert res["success"] is True
    assert res["summary"]["total_nodes"] == 0
    assert len(res["nodes"]) == 0


def test_context_manager_bot_query_populated(tmp_path: Path) -> None:
    ctx_dir = tmp_path / ".hath0r" / "context"
    ctx_dir.mkdir(parents=True)
    session_file = ctx_dir / "session.json"
    session_data = {
        "schema_version": "hath0r.contextgraph/1",
        "session_id": "sess-test-123",
        "active_subagent_id": "subagent-worker-1",
        "nodes": [
            {"id": "agent-root", "type": "agent", "label": "Main Orchestrator", "state": "running"},
            {"id": "subagent-worker-1", "type": "subagent", "label": "Worker 1", "state": "running"},
            {"id": "tool-exec-1", "type": "tool_invocation", "label": "invoke:view_file", "state": "completed", "properties": {"tool": "view_file"}},
            {"id": "jev-guard-1", "type": "jev_guard", "label": "jev:allowed", "state": "completed", "properties": {"status": "allowed"}},
        ],
        "edges": [
            {"source": "agent-root", "target": "subagent-worker-1", "relation": "delegated_to"},
            {"source": "subagent-worker-1", "target": "tool-exec-1", "relation": "executed_tool"},
            {"source": "tool-exec-1", "target": "jev-guard-1", "relation": "guarded_by"},
        ],
    }
    session_file.write_text(json.dumps(session_data, indent=2))

    bot = ContextManagerBot(cwd=tmp_path)
    res = bot.query_context()
    assert res["success"] is True
    assert res["session_id"] == "sess-test-123"
    assert res["summary"]["total_nodes"] == 4
    assert res["summary"]["subagents"] == 2
    assert res["summary"]["tool_invocations"] == 1
    assert res["summary"]["jev_guards"] == 1

    # Filter by type
    res_sub = bot.query_context(node_type="subagent")
    assert any(n["id"] == "subagent-worker-1" for n in res_sub["nodes"])

    # Filter by query
    res_jev = bot.query_context(filter_query="jev")
    assert any(n["id"] == "jev-guard-1" for n in res_jev["nodes"])


def test_context_cli_query_commands(tmp_path: Path) -> None:
    runner = CliRunner(mix_stderr=False)
    with runner.isolated_filesystem(temp_dir=tmp_path):
        # Empty context
        res_empty = runner.invoke(main, ["--output", "json", "context", "query"])
        assert res_empty.exit_code == 0
        data_empty = json.loads(res_empty.stdout)
        assert data_empty["state"] == "ok"
        assert data_empty["data"]["summary"]["total_nodes"] == 0

        # Initialize mock context session
        ctx_dir = Path.cwd() / ".hath0r" / "context"
        ctx_dir.mkdir(parents=True, exist_ok=True)
        (ctx_dir / "session.json").write_text(
            json.dumps(
                {
                    "session_id": "test-cli-sess",
                    "nodes": [
                        {"id": "agent-main", "type": "agent", "label": "Root Agent"},
                        {"id": "tool-run", "type": "tool_invocation", "label": "invoke:run_command"},
                    ],
                    "edges": [
                        {"source": "agent-main", "target": "tool-run", "relation": "executed_tool"}
                    ],
                }
            )
        )

        # JSON mode
        res_json = runner.invoke(main, ["--output", "json", "context", "query"])
        assert res_json.exit_code == 0
        data_json = json.loads(res_json.stdout)
        assert data_json["state"] == "ok"
        assert len(data_json["data"]["nodes"]) == 2

        # Text mode
        res_text = runner.invoke(main, ["--output", "text", "context", "query", "--filter", "run_command"])
        assert res_text.exit_code == 0
        assert "invoke:run_command" in res_text.stdout


def test_memory_search_and_graph_traversal(tmp_path: Path) -> None:
    bot = MemoryManagerBot(cwd=tmp_path)
    init_res = bot.initialize_memory()
    assert init_res["success"] is True

    # Search all
    all_res = bot.search_memory()
    assert all_res["success"] is True
    assert all_res["total_matches"] >= 3

    # Search specific rule
    rule_res = bot.search_memory(query="CLI", node_type="rule")
    assert rule_res["success"] is True
    assert any(n["id"] == "rule:cr-cli-entry-001" for n in rule_res["nodes"])

    # Search with edge traversal
    subgraph_res = bot.search_memory(query="CLI", depth=1)
    assert len(subgraph_res["edges"]) >= 1
    assert subgraph_res["edges"][0]["relation"] == "ENFORCES"


def test_memory_cli_search_command(tmp_path: Path) -> None:
    runner = CliRunner(mix_stderr=False)
    with runner.isolated_filesystem(temp_dir=tmp_path):
        runner.invoke(main, ["memory", "init"])

        # JSON mode
        res_json = runner.invoke(main, ["--output", "json", "memory", "search", "Promotion"])
        assert res_json.exit_code == 0
        data_json = json.loads(res_json.stdout)
        assert data_json["state"] == "ok"
        assert data_json["data"]["total_matches"] >= 1
        assert "rule:cr-bai-001" in [n["id"] for n in data_json["data"]["nodes"]]

        # Text mode
        res_text = runner.invoke(main, ["--output", "text", "memory", "search", "Tri-Graph", "--type", "concept"])
        assert res_text.exit_code == 0
        assert "concept:tri-graph" in res_text.stdout or "Tri-Graph" in res_text.stdout
