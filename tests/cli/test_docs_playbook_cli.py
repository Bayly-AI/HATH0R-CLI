"""CLI tests for `hath0r docs` and `hath0r playbook`."""

from __future__ import annotations

import pytest
from click.testing import CliRunner

import hath0r_cli.bots as bots
from hath0r_cli.cli import main
from tests.fakebot import patch_bot


def _run(fmt: str, *args: str, input: str | None = None):
    res = CliRunner().invoke(main, ["-o", fmt, *args], input=input)
    assert res.exception is None or isinstance(res.exception, SystemExit), res.output
    return res


DOCS_CASES = [
    (
        ("docs", "wiki", "--repo", "o/r", "--title", "T", "--body", "b"),
        {"success": True, "skipped": True, "reason": "off"},
        0,
    ),
    (
        ("docs", "wiki", "--repo", "o/r", "--title", "T", "--pr", "3", "--force"),
        {"success": True, "action": "synced"},
        0,
    ),
    (("docs", "wiki", "--repo", "o/r", "--title", "T", "--dry-run"), {"success": False, "error": "no wiki"}, 1),
    (("docs", "share", "--pr", "7", "--repo", "o/r", "--dry-run"), {"success": True, "path": "/kb/7.md"}, 0),
    (("docs", "share", "--summary", "s", "--target-kb", "/kb"), {"success": False, "error": "kb missing"}, 1),
    (
        (
            "docs",
            "share",
        ),
        {"success": True, "reason": "already shared"},
        0,
    ),
]


@pytest.mark.parametrize("fmt", ["text", "json"], ids=["text", "json"])
@pytest.mark.parametrize("args,result,code", DOCS_CASES, ids=[f"docs{i}" for i in range(len(DOCS_CASES))])
def test_docs_commands(monkeypatch, fmt, args, result, code):
    patch_bot(monkeypatch, bots, "DocumentationBot", result)
    assert _run(fmt, *args, input="piped body").exit_code == code


@pytest.mark.parametrize("fmt", ["text", "json"], ids=["text", "json"])
def test_playbook_commands(tmp_path, monkeypatch, fmt):
    pb = tmp_path / "docs" / "governance" / "playbooks"
    pb.mkdir(parents=True)
    (pb / "playbook-troubleshooting.md").write_text("# Troubleshooting\n\n- step one\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    assert "playbook-troubleshooting" in _run(fmt, "playbook", "list").output
    assert "Troubleshooting" in _run(fmt, "playbook", "read", "playbook-troubleshooting").output
    assert _run(fmt, "playbook", "read", "absent").output.strip()
