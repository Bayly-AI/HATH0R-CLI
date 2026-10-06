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


def _setup_sonar(tmp_path: Path) -> None:
    (tmp_path / "sonar-project.properties").write_text(
        "sonar.projectKey=Bayly-AI_Test\nsonar.organization=bayly-ai\n",
        encoding="utf-8",
    )
    wf_dir = tmp_path / ".github" / "workflows"
    wf_dir.mkdir(parents=True, exist_ok=True)
    (wf_dir / "sonarcloud-quality-gate.yml").write_text("name: SonarCloud Quality Gate\n", encoding="utf-8")


def _fake_git(branch: str):
    def fake_run_cmd(args, cwd=None):
        if args[:3] == ["git", "branch", "--show-current"]:
            return 0, branch, ""
        if args[:2] == ["git", "status"]:
            return 0, "", ""
        return 1, "", "unexpected"

    return fake_run_cmd


def _branch_check(res):
    return next(c for c in res["checks"] if c.get("check") == "branch")


def test_preflight_sonar_config_missing(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "VERSION").write_text("0.7.0\n", encoding="utf-8")
    monkeypatch.setattr("hath0r_cli.bots.quality.run_cmd", _fake_git("fix/278-preflight-sonar"))
    res = PreflightBot(cwd=tmp_path).run(skip_tests=True)
    sonar_check = next(c for c in res["checks"] if c.get("check") == "sonar_config")
    assert sonar_check["ok"] is False
    assert "sonar-project.properties missing" in sonar_check["error"]
    assert res["success"] is False


def test_preflight_accepts_release_branch_matching_version(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "VERSION").write_text("0.7.0\n", encoding="utf-8")
    _setup_sonar(tmp_path)
    monkeypatch.setattr("hath0r_cli.bots.quality.run_cmd", _fake_git("release/0.7.0"))
    res = PreflightBot(cwd=tmp_path).run(skip_tests=True)
    check = _branch_check(res)
    assert check["ok"] is True
    assert check["is_release"] is True
    assert check["version"] == "0.7.0"
    assert res["success"] is True


def test_preflight_rejects_release_branch_version_mismatch(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "VERSION").write_text("0.6.0\n", encoding="utf-8")
    _setup_sonar(tmp_path)
    monkeypatch.setattr("hath0r_cli.bots.quality.run_cmd", _fake_git("release/0.7.0"))
    res = PreflightBot(cwd=tmp_path).run(skip_tests=True)
    check = _branch_check(res)
    assert check["ok"] is False
    assert "does not match VERSION '0.6.0'" in check["error"]
    assert res["success"] is False


def test_preflight_rejects_untaxonomic_branch(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "VERSION").write_text("0.7.0\n", encoding="utf-8")
    _setup_sonar(tmp_path)
    monkeypatch.setattr("hath0r_cli.bots.quality.run_cmd", _fake_git("my-random-branch"))
    res = PreflightBot(cwd=tmp_path).run(skip_tests=True)
    check = _branch_check(res)
    assert check["ok"] is False
    assert "release/<semver>" in check["error"]


def test_preflight_accepts_issue_branch(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "VERSION").write_text("0.7.0\n", encoding="utf-8")
    _setup_sonar(tmp_path)
    monkeypatch.setattr("hath0r_cli.bots.quality.run_cmd", _fake_git("fix/278-preflight-release-branches"))
    res = PreflightBot(cwd=tmp_path).run(skip_tests=True)
    check = _branch_check(res)
    assert check["ok"] is True
    assert check["issue_number"] == 278
    assert check["prefix"] == "fix"
    assert res["success"] is True


def test_deploy_test_bot_parse_pytest_output() -> None:
    from hath0r_cli.bots.quality import DeployTestBot

    sample_stdout = """
============================= test session starts ==============================
rootdir: /path/to/repo
collected 42 items

tests/unit/test_one.py ...........                                       [ 26%]
tests/unit/test_two.py F..                                               [ 33%]
tests/unit/test_three.py ............................                    [100%]

=================================== FAILURES ===================================
___________________________________ test_fail __________________________________
FAILED tests/unit/test_two.py::test_fail - AssertionError: assert 1 == 2
======================== 1 failed, 41 passed in 1.25s ==========================
"""
    metrics = DeployTestBot._parse_test_output(sample_stdout, "")
    assert metrics["passed"] == 41
    assert metrics["failed"] == 1
    assert len(metrics["failures"]) == 1
    assert metrics["failures"][0]["test"] == "tests/unit/test_two.py::test_fail"
    assert "AssertionError" in metrics["failures"][0]["detail"]


def test_deploy_test_bot_dry_run() -> None:
    from hath0r_cli.bots.quality import DeployTestBot

    bot = DeployTestBot()
    res = bot.run_pre_deploy(dry_run=True)
    assert res["success"] is True
    assert res["dry_run"] is True
    assert res["phase"] == "pre_deploy"


def test_end_of_task_daemon_bot_test_suite_failure(tmp_path: Path, monkeypatch) -> None:
    from hath0r_cli.bots import EndOfTaskBot

    daemon_bot = EndOfTaskBot(cwd=tmp_path)

    # Mock DeployTestBot to fail
    def fake_run_pre_deploy(dry_run=False):
        return {
            "success": False,
            "phase": "pre_deploy",
            "issues": [{"test": "tests/unit/test_fail.py::test_bad", "detail": "AssertionError"}],
            "total_passed": 10,
            "total_failed": 1,
            "total_errors": 0,
            "message": "pre_deploy failed",
        }

    monkeypatch.setattr(daemon_bot.test_bot, "run_pre_deploy", fake_run_pre_deploy)

    res = daemon_bot.run_bot(branch="feature/145-test", semver="patch", dry_run=False)
    assert res["success"] is False
    assert res["phase"] == "test_suite"
    assert "Local test suite failed" in res["error"]
    assert len(res["issues"]) == 1


def test_cli_deploy_pre_dry_run() -> None:
    runner = CliRunner(mix_stderr=False)
    res = runner.invoke(cli.main, ["--output", "json", "deploy", "pre", "--dry-run"])
    assert res.exit_code == 0
    data = json.loads(res.stdout)
    assert data["state"] == "ok"
    assert data["data"]["dry_run"] is True


def test_quality_gate_check_sonar_mocked(tmp_path: Path, monkeypatch) -> None:
    bot = QualityGateBot(cwd=tmp_path)
    (tmp_path / "sonar-project.properties").write_text(
        "sonar.projectKey=Bayly-AI_Test\nsonar.organization=bayly-ai\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("SONAR_TOKEN", "mock_token")

    class FakeResponse:
        def __init__(self, data: dict):
            self.data = json.dumps(data).encode("utf-8")

        def read(self):
            return self.data

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

    import urllib.request

    def fake_urlopen(req):
        url = req.full_url if hasattr(req, "full_url") else str(req)
        if "project_status" in url:
            return FakeResponse({"projectStatus": {"status": "OK", "conditions": []}})
        return FakeResponse({"issues": []})

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    res = bot.check_sonar()
    assert res["success"] is True
    assert res["status"] == "OK"
    assert "OK" in res["message"]


def test_cli_quality_sonar_mocked(tmp_path: Path, monkeypatch) -> None:
    runner = CliRunner(mix_stderr=False)
    monkeypatch.setenv("SONAR_TOKEN", "mock_token")

    class FakeResponse:
        def __init__(self, data: dict):
            self.data = json.dumps(data).encode("utf-8")

        def read(self):
            return self.data

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

    import urllib.request

    def fake_urlopen(req):
        url = req.full_url if hasattr(req, "full_url") else str(req)
        if "project_status" in url:
            return FakeResponse({
                "projectStatus": {
                    "status": "ERROR",
                    "conditions": [{"status": "ERROR", "metricKey": "new_security_rating", "actualValue": "5", "errorThreshold": "1", "comparator": "GT"}],
                }
            })
        return FakeResponse({"issues": [{"severity": "BLOCKER", "component": "src/foo.py", "line": 10, "message": "SQL Injection", "rule": "python:S3649"}]})

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    res = runner.invoke(cli.main, ["--output", "json", "quality", "sonar", "--project-key", "Bayly-AI_Test"])
    assert res.exit_code == 1
    data = json.loads(res.stdout)
    assert data["state"] == "error"
    assert data["data"]["status"] == "ERROR"
    assert len(data["data"]["blocking_issues"]) == 1

