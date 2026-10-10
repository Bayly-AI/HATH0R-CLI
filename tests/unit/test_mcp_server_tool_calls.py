"""Regression tests: the FastMCP tools added in 1.1.0 must call their bots with real signatures (#392)."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

pytest.importorskip("mcp")

from hath0r_cli.server.mcp_server import create_mcp_server  # noqa: E402


def _tool(name: str) -> Any:
    server = create_mcp_server()
    return server._tool_manager._tools[name].fn


def test_upgrade_check_passes_version() -> None:
    with patch("hath0r_cli.bots.upgrade_bot.UpgradeBot") as bot_cls:
        bot_cls.return_value.check.return_value = {"success": True}
        assert _tool("hath0r_upgrade")(action="check", target_version="1.2.0") == {"success": True}
        bot_cls.return_value.check.assert_called_once_with(version="1.2.0")


def test_upgrade_rollback_is_explained_not_crashing() -> None:
    res = _tool("hath0r_upgrade")(action="rollback")
    assert res["success"] is False
    assert "automatic" in res["error"]


def test_clean_repos_dry_run_makes_no_changes(tmp_path: Path) -> None:
    with patch("hath0r_cli.bots.repo_clean.CleanReposWorkflowBot") as bot_cls:
        res = _tool("hath0r_clean_repos")(repo_path=str(tmp_path), dry_run=True)
    assert res["dry_run"] is True
    bot_cls.assert_not_called()


def test_clean_repos_executes_without_auto_commit(tmp_path: Path) -> None:
    with patch("hath0r_cli.bots.repo_clean.CleanReposWorkflowBot") as bot_cls:
        bot_cls.return_value.run_clean_repo_workflow.return_value = {"ok": True}
        _tool("hath0r_clean_repos")(repo_path=str(tmp_path), dry_run=False)
    bot_cls.assert_called_once_with(cwd=tmp_path)
    bot_cls.return_value.run_clean_repo_workflow.assert_called_once_with(target_repos=[tmp_path], auto_commit=False)


def test_contracts_validate_uses_target_dir(tmp_path: Path) -> None:
    with patch("hath0r_cli.bots.contracts_bot.ContractsBot") as bot_cls:
        _tool("hath0r_contracts_validate")(contracts_dir=str(tmp_path))
    bot_cls.return_value.validate_contracts.assert_called_once_with(target_dir=tmp_path)


def test_pr_review_fetches_diff_and_reviews_it() -> None:
    with patch("subprocess.check_output", return_value=b"+x = 1\n") as co, patch(
        "hath0r_cli.bots.antagonistic_review.AntagonisticReviewBot"
    ) as bot_cls:
        _tool("hath0r_pr_review_antagonistic")(pr_number=7, repo="o/r")
    assert co.call_args[0][0] == ["gh", "pr", "diff", "7", "-R", "o/r"]
    bot_cls.return_value.review_diff.assert_called_once_with(diff_content="+x = 1\n")


def test_pr_review_reports_fetch_failure() -> None:
    with patch("subprocess.check_output", side_effect=OSError("gh missing")):
        res = _tool("hath0r_pr_review_antagonistic")(pr_number=7)
    assert res["success"] is False


def test_kb_smart_query_passes_top_k() -> None:
    with patch("hath0r_cli.bots.cag_rag_router.HybridCAGRAGRouter") as router_cls:
        router_cls.return_value.route_query.return_value = {"matches": [1, 2, 3]}
        res = _tool("hath0r_kb_smart_query")(query="q", top_k=3)
    router_cls.return_value.route_query.assert_called_once_with("q", top_k=3)
    assert res["matches"] == [1, 2, 3]


def test_finops_budget_check_estimates_prompt() -> None:
    res = _tool("hath0r_finops_budget_check")(prompt="x" * 400, session_id="s1")
    assert res["tree_id"] == "s1"
    assert res["prompt_tokens_estimate"] == 100
    assert res["within_budget"] is True


def test_evals_redteam_maps_arguments() -> None:
    with patch("hath0r_cli.bots.redteam_engine.MultiAgentRedTeamEngine") as eng_cls:
        eng_cls.return_value.run_redteam_verification.return_value = MagicMock()
        _tool("hath0r_evals_redteam")(scenario="agent_subsystem", rounds=2)
    eng_cls.return_value.run_redteam_verification.assert_called_once_with(
        component_name="agent_subsystem", stress_iterations=2
    )
