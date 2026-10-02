"""Unit tests for DynamicToolRouter, SchemaPruner, and MCP route/prune CLI commands."""

import json
import tempfile
from pathlib import Path

from click.testing import CliRunner

from hath0r_cli.cli import main as cli
from hath0r_cli.mcp import DynamicToolRouter, SchemaPruner


def test_schema_pruner_compression():
    """Verify SchemaPruner compresses schema while preserving required fields and types."""
    pruner = SchemaPruner(max_desc_len=50)

    sample_tool = {
        "name": "git_branch_validate",
        "description": "A very long detailed verbose description that exceeds the normal budget allowed for agent prompts.",
        "inputSchema": {
            "type": "object",
            "required": ["branch_name"],
            "properties": {
                "branch_name": {
                    "type": "string",
                    "description": "The exact target git branch string to validate against governance rules.",
                },
                "fix": {
                    "type": "boolean",
                    "default": False,
                    "description": "Whether to automatically fix the branch slug.",
                },
            },
        },
    }

    pruned = pruner.prune(sample_tool)
    assert pruned["name"] == "git_branch_validate"
    assert len(pruned["description"]) <= 50
    assert "parameters" in pruned
    assert pruned["parameters"]["type"] == "object"
    assert "branch_name" in pruned["parameters"]["required"]
    assert pruned["parameters"]["properties"]["branch_name"]["type"] == "string"
    assert pruned["parameters"]["properties"]["fix"]["default"] is False


def test_dynamic_tool_router_selection():
    """Verify DynamicToolRouter ranks and selects the most relevant tools for a task."""
    tools = [
        {"name": "git_branch_validate", "description": "Validate git branch naming.", "parameters": {}},
        {"name": "gh_pr_create", "description": "Create a GitHub pull request.", "parameters": {}},
        {"name": "vision_inspect", "description": "Inspect and parse visual UI mockups.", "parameters": {}},
        {"name": "kb_search", "description": "Search canonical knowledgebase documents.", "parameters": {}},
    ]

    router = DynamicToolRouter(tools)

    # Search for git task
    git_results = router.route("create pull request for git branch", top_k=2)
    assert len(git_results) <= 2
    tool_names = [t["name"] for t in git_results]
    assert "gh_pr_create" in tool_names or "git_branch_validate" in tool_names

    # Search for vision task
    vision_results = router.route("inspect image diagram", top_k=1)
    assert len(vision_results) == 1
    assert vision_results[0]["name"] == "vision_inspect"


def test_mcp_route_cli():
    """Verify hath0r mcp route CLI execution."""
    runner = CliRunner()
    res = runner.invoke(cli, ["-o", "text", "mcp", "route", "--intent", "validate git branch and open PR", "--top-k", "2"])
    assert res.exit_code == 0
    assert "Top" in res.output or "git_branch_validate" in res.output


def test_mcp_prune_cli():
    """Verify hath0r mcp prune CLI execution."""
    runner = CliRunner()
    with tempfile.TemporaryDirectory() as tmp_dir:
        schema_file = Path(tmp_dir) / "test_schema.json"
        schema_data = {
            "name": "test_tool",
            "description": "An excessively wordy description that will be pruned down by the CLI pruner.",
            "parameters": {
                "type": "object",
                "required": ["id"],
                "properties": {"id": {"type": "string", "description": "Identifier"}},
            },
        }
        schema_file.write_text(json.dumps(schema_data), encoding="utf-8")

        res = runner.invoke(cli, ["-o", "text", "mcp", "prune", str(schema_file)])
        assert res.exit_code == 0
        assert "Pruned" in res.output
