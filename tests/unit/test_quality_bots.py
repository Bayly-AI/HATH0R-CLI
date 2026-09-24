"""Tests for Factory Manager, quality, preflight, release, and docs bots."""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from hath0r_cli import cli
from hath0r_cli.bots import DocumentationBot
from hath0r_cli.bots.quality import PreflightBot, QualityGateBot, ReleaseBot
from hath0r_cli.factory_manager import FactoryManagerBot


def test_quality_gate_evaluate_rollup_pass() -> None:
    bot = QualityGateBot()
    rollup = [
        {"name": "SonarCloud Quality Gate", "conclusion": "SUCCESS"},
        {"name": "validate-promotion-path", "conclusion": "SUCCESS"},
        {"name": "pr-workflow-guard", "conclusion": "SUCCESS"},
        {"name": "unit-tests", "conclusion": "SUCCESS"},
    ]
    res = bot.evaluate_rollup(rollup)
    assert res["ready_to_merge"] is True
    assert res["hard_failures"] == []
    assert res["hard_missing"] == []


def test_quality_gate_missing_sonar() -> None:
    bot = QualityGateBot()
    res = bot.evaluate_rollup(
        [
            {"name": "validate-promotion-path", "conclusion": "SUCCESS"},
            {"name": "pr-workflow-guard", "conclusion": "SUCCESS"},
        ]
    )
    assert res["ready_to_merge"] is False
    assert "SonarCloud Quality Gate" in res["hard_missing"]


def test_quality_gate_failure() -> None:
    bot = QualityGateBot()
    res = bot.evaluate_rollup(
        [
            {"name": "SonarCloud Quality Gate", "conclusion": "FAILURE"},
            {"name": "validate-promotion-path", "conclusion": "SUCCESS"},
            {"name": "pr-workflow-guard", "conclusion": "SUCCESS"},
        ]
    )
    assert res["success"] is False
    assert "SonarCloud Quality Gate" in res["hard_failures"]


def test_release_bot_read_version(tmp_path: Path) -> None:
    (tmp_path / "VERSION").write_text("1.2.3\n", encoding="utf-8")
    (tmp_path / "CHANGELOG.md").write_text("## [1.2.3]\n\n- item\n", encoding="utf-8")
    bot = ReleaseBot(cwd=tmp_path)
    assert bot.read_version()["version"] == "1.2.3"
    assert bot.validate()["success"] is True
    notes = bot.generate_notes()
    assert notes["success"] is True
    assert "item" in notes["notes"]


def test_release_bot_dry_run_publish(tmp_path: Path) -> None:
    (tmp_path / "VERSION").write_text("0.9.0\n", encoding="utf-8")
    (tmp_path / "CHANGELOG.md").write_text("## [0.9.0]\n\nnotes\n", encoding="utf-8")
    bot = ReleaseBot(cwd=tmp_path)
    res = bot.tag_and_release(dry_run=True)
    assert res["success"] is True
    assert res["dry_run"] is True
    assert res["tag"] == "v0.9.0"


def test_factory_manager_crud(tmp_path: Path) -> None:
    factories = tmp_path / "cfg" / "factories"
    factories.mkdir(parents=True)
    bot = FactoryManagerBot(cwd=tmp_path)
    created = bot.create("demo-factory", name="Demo", dry_run=False)
    assert created["success"] is True
    assert (factories / "demo-factory.yaml").is_file()
    listed = bot.list_factories()
    assert any(i["id"] == "demo-factory" for i in listed)
    updated = bot.update("demo-factory", description="updated")
    assert updated["success"] is True
    deleted = bot.delete("demo-factory")
    assert deleted["success"] is True
    assert not (factories / "demo-factory.yaml").is_file()


def test_factory_create_cli_dry_run() -> None:
    runner = CliRunner(mix_stderr=False)
    res = runner.invoke(
        cli.main,
        ["--output", "json", "factory", "create", "tmp-cli-factory", "--dry-run"],
    )
    assert res.exit_code == 0
    data = json.loads(res.stdout)
    assert data["state"] == "ok"
    assert data["data"]["dry_run"] is True


def test_cli_quality_check_dry_run() -> None:
    runner = CliRunner(mix_stderr=False)
    res = runner.invoke(cli.main, ["--output", "json", "quality", "check", "1", "--dry-run"])
    assert res.exit_code == 0
    data = json.loads(res.stdout)
    assert data["data"]["dry_run"] is True


def test_cli_preflight_dry_run() -> None:
    runner = CliRunner(mix_stderr=False)
    res = runner.invoke(cli.main, ["--output", "json", "preflight", "run", "--dry-run"])
    assert res.exit_code == 0
    data = json.loads(res.stdout)
    assert data["data"]["dry_run"] is True


def test_cli_release_validate() -> None:
    runner = CliRunner(mix_stderr=False)
    res = runner.invoke(cli.main, ["--output", "json", "release", "validate"])
    # VERSION 0.2.0 is in CHANGELOG for this repo
    assert res.exit_code == 0
    data = json.loads(res.stdout)
    assert data["state"] == "ok"


def test_docs_share_dry_run(tmp_path: Path) -> None:
    bot = DocumentationBot(cwd=tmp_path)
    (tmp_path / "cfg").mkdir()
    (tmp_path / "cfg" / "quality-gates.json").write_text(
        json.dumps({"knowledge_share": {"enabled": True}}),
        encoding="utf-8",
    )
    res = bot.share_knowledge(summary="hello", pr_number=42, dry_run=True)
    assert res["success"] is True
    assert res["dry_run"] is True
    assert res["key"] == "pr-42"


def test_docs_wiki_skipped_when_disabled(tmp_path: Path) -> None:
    bot = DocumentationBot(cwd=tmp_path)
    (tmp_path / "cfg").mkdir()
    (tmp_path / "cfg" / "quality-gates.json").write_text(
        json.dumps({"wiki": {"enabled": False}}),
        encoding="utf-8",
    )
    res = bot.sync_to_wiki("Bayly-AI/HATH0R-CLI", "Title", "# body", pr_number=9)
    assert res.get("skipped") is True


def test_bot_registry_includes_quality_bots() -> None:
    from hath0r_cli.step_runner import BotRegistry

    reg = BotRegistry()
    for bot_id in (
        "factory-manager-bot",
        "quality-gate-bot",
        "preflight-bot",
        "deploy-test-bot",
        "release-bot",
    ):
        assert bot_id in reg.registered_bot_ids()

    res = reg.invoke("quality-gate-bot", "evaluate-rollup", {"status_checks": []})
    # Missing hard gates → not ready
    assert res.success is False


def test_preflight_branch_check_on_canonical(tmp_path: Path, monkeypatch) -> None:
    bot = PreflightBot(cwd=tmp_path)
    (tmp_path / "VERSION").write_text("1.0.0\n", encoding="utf-8")

    def fake_run_cmd(args, cwd=None):
        if args[:3] == ["git", "branch", "--show-current"]:
            return 0, "development", ""
        if args[:2] == ["git", "status"]:
            return 0, "", ""
        return 1, "", "unexpected"

    monkeypatch.setattr("hath0r_cli.bots.quality.run_cmd", fake_run_cmd)
    res = bot.run(skip_tests=True)
    assert res["success"] is False
    assert any(c.get("check") == "branch" and not c.get("ok") for c in res["checks"])
