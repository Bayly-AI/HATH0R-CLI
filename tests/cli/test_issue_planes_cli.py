"""CLI tests for `hath0r issue`, `hath0r planes` and `hath0r schema`."""

from __future__ import annotations

import json

import pytest
from click.testing import CliRunner

from hath0r_cli.bots.issue_manager import IssueManagerBot
from hath0r_cli.cli import main

LISTING = {
    "success": True,
    "repo_count": 2,
    "total_issues": 2,
    "valid_issues": 1,
    "issues": [
        {
            "priority_rank": 1,
            "priority_label": "P1",
            "repository": "Bayly-AI/HATH0R-CLI",
            "number": 10,
            "title": "Fix the thing",
            "state": "OPEN",
            "depends_on": [9],
            "blocks": [11],
            "validation": {"is_valid": True},
        },
        {
            "priority_rank": 2,
            "repository": "Bayly-AI/HATH0R-CLI",
            "number": 12,
            "title": "Short",
            "validation": {"is_valid": False, "findings": ["title too short"]},
        },
    ],
}


def _run(*args: str):
    return CliRunner().invoke(main, list(args))


@pytest.mark.parametrize("mode", ["text", "json"])
def test_issue_list(monkeypatch, mode):
    monkeypatch.setattr(IssueManagerBot, "list_issues", lambda self, **kw: dict(LISTING))
    res = _run("-o", mode, "issue", "list", "--state", "all")
    assert res.exit_code == 0, res.output
    if mode == "json":
        assert json.loads(res.output)["command"] == "issue.list"
    else:
        assert "BaylyAI Issue Factory" in res.output
        assert "depends on #9" in res.output
        assert "title too short" in res.output


def test_issue_list_dry_run_and_failure(monkeypatch):
    monkeypatch.setattr(
        IssueManagerBot, "list_issues", lambda self, **kw: {"success": True, "action": "would list issues"}
    )
    res = _run("-o", "text", "issue", "list", "--dry-run")
    assert res.exit_code == 0
    assert "would list issues" in res.output

    monkeypatch.setattr(IssueManagerBot, "list_issues", lambda self, **kw: {"success": False})
    assert _run("-o", "json", "issue", "list").exit_code == 1


@pytest.mark.parametrize(
    "result, code, text",
    [
        ({"success": True, "issue_number": 5, "repo": "o/r", "url": "https://x/5"}, 0, "Created issue #5"),
        ({"success": False, "error": "body too short"}, 1, "body too short"),
    ],
)
def test_issue_create(monkeypatch, result, code, text):
    seen = {}

    def fake_create(self, **kw):
        seen.update(kw)
        return result

    monkeypatch.setattr(IssueManagerBot, "create_issue", fake_create)
    res = _run("-o", "text", "issue", "create", "--repo", "o/r", "--title", "A useful title", "--body", "b", "-l", "bug")
    assert res.exit_code == code
    assert text in res.output
    assert seen["labels"] == ["bug"]


@pytest.mark.parametrize("mode", ["text", "json"])
def test_planes(mode):
    res = _run("-o", mode, "planes")
    assert res.exit_code == 0, res.output
    if mode == "json":
        assert json.loads(res.output)["command"] == "planes"


@pytest.mark.parametrize("status", ["all", "shipped", "planned"])
def test_schema_filters(status):
    res = _run("-o", "json", "schema", "--status", status)
    assert res.exit_code == 0, res.output
    data = json.loads(res.output)["data"]
    assert data["binary"] == "hath0r"
    if status != "all":
        assert all(c["status"] == status for c in data["commands"])


def test_schema_text():
    res = _run("-o", "text", "schema")
    assert res.exit_code == 0
    assert "Total commands listed" in res.output
