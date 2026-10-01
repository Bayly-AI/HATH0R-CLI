"""Unit tests for IssueManagerBot and issue-factory."""

from __future__ import annotations

from pathlib import Path

import yaml

from hath0r_cli.bots.issue_manager import (
    IssueManagerBot,
    resolve_baylyai_repos,
)
from hath0r_cli.step_runner import BotRegistry


def test_resolve_baylyai_repos_default():
    repos = resolve_baylyai_repos(None)
    assert len(repos) >= 16
    assert "Bayly-AI/HATH0R-CLI" in repos
    assert "Bayly-AI/baylyai-uxp" in repos
    assert "Bayly-AI/1-Nation-ATC-Wiki" in repos
    assert "Bayly-AI/1-Nation" in repos
    assert "Bayly-AI/1-Nation-ATC" in repos
    assert "Bayly-AI/1-Nation-MCP" in repos


def test_resolve_baylyai_repos_specific():
    repos = resolve_baylyai_repos("HATH0R-CLI")
    assert repos == ["Bayly-AI/HATH0R-CLI"]

    repos_full = resolve_baylyai_repos("Bayly-AI/1-Nation")
    assert repos_full == ["Bayly-AI/1-Nation"]


def test_issue_manager_bot_validate_description_and_status():
    bot = IssueManagerBot()

    # Valid issue
    valid_data = {
        "title": "feat(core): implement high-performance scheduler engine",
        "body": (
            "## Summary\n"
            "Implement a high-performance scheduler engine for Hath0r tasks with concurrency controls.\n\n"
            "## Acceptance Criteria\n- Clean benchmarks\n- Full unit test coverage"
        ),
        "state": "OPEN",
    }
    val = bot.validate_issue_data(valid_data)
    assert val["is_valid"] is True
    assert val["status"] == "OPEN"
    assert len(val["findings"]) == 0

    # Invalid issue: title too short, body lacking detail
    invalid_data = {
        "title": "bug",
        "body": "Fix it",
        "state": "OPEN",
    }
    val2 = bot.validate_issue_data(invalid_data)
    assert val2["is_valid"] is False
    assert any("Title too short" in f for f in val2["findings"])
    assert any("Description lacks detail" in f for f in val2["findings"])


def test_issue_manager_bot_structure_priorities():
    bot = IssueManagerBot()

    issues = [
        {
            "number": 10,
            "title": "Application feature that depends on core",
            "body": "Needs ticket #20 to complete first. Depends on #20.",
            "repository": "Bayly-AI/baylyai-uxp",
            "state": "OPEN",
            "labels": [],
        },
        {
            "number": 20,
            "title": "Core foundation API",
            "body": "Provides core engine API. Blocks #10.",
            "repository": "Bayly-AI/HATH0R-CLI",
            "state": "OPEN",
            "labels": [],
        },
        {
            "number": 30,
            "title": "Epic: Multi-model support",
            "body": "Tracking umbrella epic ticket for multi-model infrastructure.",
            "repository": "Bayly-AI/HATH0R-Agentic-Framework",
            "state": "OPEN",
            "labels": [{"name": "epic"}],
        },
    ]

    prioritized = bot.structure_priorities(issues)
    assert len(prioritized) == 3

    # Issue #20 blocks another ticket, so it should receive highest priority tier (P1)
    assert prioritized[0]["number"] == 20
    assert prioritized[0]["priority_tier"] == 1
    assert prioritized[0]["priority_label"] == "P1-Blocker/Core"

    # Issue #10 is blocked by #20, so it receives lower tier
    issue_10 = next(i for i in prioritized if i["number"] == 10)
    assert issue_10["priority_tier"] == 4
    assert issue_10["priority_label"] == "P4-Blocked-By-Dependencies"


def test_issue_factory_manifest_and_registry():
    manifest_path = Path(__file__).resolve().parents[2] / "cfg" / "factories" / "issue-factory.yaml"
    assert manifest_path.is_file()

    data = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    assert data["factory_id"] == "issue-factory"
    assert "issue-manager-bot" in [b["id"] for b in data.get("bots", [])]

    registry = BotRegistry()
    assert "issue-manager-bot" in registry.registered_bot_ids()
    assert isinstance(registry.get_bot("issue-manager-bot"), IssueManagerBot)

    step_res = registry.invoke("issue-manager-bot", "list-issues", {"repo": "Bayly-AI/HATH0R-CLI"}, dry_run=True)
    assert step_res.success is True
    assert step_res.dry_run is True
