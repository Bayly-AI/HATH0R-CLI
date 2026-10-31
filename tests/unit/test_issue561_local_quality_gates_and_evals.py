"""Unit tests for Issue #561: Local Quality Gates (thresholds.json) & TaskEvaluatorBot integration."""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from hath0r_cli.bots.local_quality_gate_bot import (
    SONARCLOUD_CANONICAL_THRESHOLDS,
    LocalQualityGateBot,
)
from hath0r_cli.bots.task_evaluator_bot import TaskEvaluatorBot
from hath0r_cli.cli import main as cli
from hath0r_cli.step_runner import BotRegistry


def test_canonical_sonarcloud_thresholds_defaults(tmp_path: Path) -> None:
    """Verify thresholds.json is provisioned with SonarCloud's canonical thresholds."""
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "demo"\n', encoding="utf-8")
    (tmp_path / "src").mkdir()
    bot = LocalQualityGateBot(cwd=tmp_path)
    cfg = bot.load_or_init_thresholds(tmp_path, create_if_missing=True)

    t_file = tmp_path / "thresholds.json"
    assert t_file.is_file()
    persisted = json.loads(t_file.read_text(encoding="utf-8"))
    assert persisted["rule_id"] == "CR-LOCAL-QGATES-001"
    assert persisted["technology"] == "python"
    assert persisted["thresholds"]["max_errors"] == 0
    assert persisted["thresholds"]["min_coverage_pct"] == 80.0
    assert persisted["thresholds"]["max_complexity"] == 15
    assert persisted["thresholds"]["max_duplicated_lines_pct"] == 3.0
    assert cfg["thresholds"] == SONARCLOUD_CANONICAL_THRESHOLDS


def test_technology_detection_and_missing_test_harness_scaffolding(tmp_path: Path) -> None:
    """Verify Hath0r detects repo technology and creates the testing system if missing."""
    # 1. Python repo without tests/ directory
    py_repo = tmp_path / "py_repo"
    py_repo.mkdir()
    (py_repo / "pyproject.toml").write_text('[project]\nname = "py-repo"\n', encoding="utf-8")
    (py_repo / "src").mkdir()
    (py_repo / "src" / "app.py").write_text("def add(a: int, b: int) -> int:\n    return a + b\n", encoding="utf-8")

    bot = LocalQualityGateBot(cwd=py_repo)
    res_py = bot.ensure_supporting_system(py_repo, install_missing=False, scaffold_missing=True)
    assert res_py["technology"] == "python"
    assert (py_repo / "thresholds.json").is_file()
    assert (py_repo / "tests" / "test_qgate_smoke.py").is_file()
    assert "tests/test_qgate_smoke.py" in res_py["scaffolded_files"]

    # 2. Node-TS repo without test/ directory
    ts_repo = tmp_path / "ts_repo"
    ts_repo.mkdir()
    (ts_repo / "package.json").write_text('{"name": "ts-repo"}', encoding="utf-8")
    (ts_repo / "tsconfig.json").write_text('{"compilerOptions": {}}', encoding="utf-8")
    (ts_repo / "src").mkdir()
    (ts_repo / "src" / "index.ts").write_text("export const greet = (name: string) => `hi ${name}`;\n", encoding="utf-8")

    res_ts = bot.ensure_supporting_system(ts_repo, install_missing=False, scaffold_missing=True)
    assert res_ts["technology"] == "node-ts"
    assert (ts_repo / "thresholds.json").is_file()
    assert (ts_repo / "test" / "qgate.smoke.test.ts").is_file()


def test_local_gates_pass_on_clean_repo(tmp_path: Path) -> None:
    """Verify all 4 Local Quality Gates pass on a clean repository with unit tests."""
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "clean-repo"\n', encoding="utf-8")
    src = tmp_path / "src"
    src.mkdir()
    (src / "calc.py").write_text(
        "def compute_total(values: list[int]) -> int:\n"
        "    total = 0\n"
        "    for item in values:\n"
        "        if item > 0:\n"
        "            total += item\n"
        "    return total\n",
        encoding="utf-8",
    )
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_calc.py").write_text(
        "from src.calc import compute_total\n\n"
        "def test_compute_total() -> None:\n"
        "    assert compute_total([1, 2, 3]) == 6\n",
        encoding="utf-8",
    )

    bot = LocalQualityGateBot(cwd=tmp_path)
    res = bot.evaluate_local_gates(tmp_path, changed_only=False, auto_init=True)
    assert res["passed"] is True
    assert res["failing_gates"] == []
    assert res["gates"]["errors"]["passed"] is True
    assert res["gates"]["coverage"]["passed"] is True
    assert res["gates"]["complexity"]["passed"] is True
    assert res["gates"]["duplication"]["passed"] is True
    assert 0.85 <= res["qgate_score"] <= 1.0


def test_local_gates_detect_errors_complexity_and_duplication_failures(tmp_path: Path) -> None:
    """Verify Local Quality Gates fail when complexity > 15 or duplicated lines > 3%."""
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "flawed-repo"\n', encoding="utf-8")
    src = tmp_path / "src"
    src.mkdir()

    # Create a deeply nested function exceeding cognitive complexity 15 + duplicated 10-line block
    dup_block = "\n".join(
        [f"    normalized_metric_value_{i} = (base_input + {i}) * 42 - {i * 3}" for i in range(12)]
    )
    complex_code = (
        "def overly_complex_and_duplicated(base_input: int) -> int:\n"
        f"{dup_block}\n"
        f"{dup_block}\n"
        "    if base_input > 0:\n"
        "        for i in range(base_input):\n"
        "            if i % 2 == 0:\n"
        "                while base_input > 10:\n"
        "                    if base_input % 3 == 0:\n"
        "                        if base_input % 5 == 0:\n"
        "                            base_input -= 1\n"
        "                    base_input -= 2\n"
        "    return base_input\n"
    )
    (src / "bad_module.py").write_text(complex_code, encoding="utf-8")

    bot = LocalQualityGateBot(cwd=tmp_path)
    res = bot.evaluate_local_gates(tmp_path, changed_only=False, auto_init=True)
    assert res["passed"] is False
    assert "complexity" in res["failing_gates"]
    assert "duplication" in res["failing_gates"]
    assert res["gates"]["complexity"]["max_observed_complexity"] > 15
    assert res["gates"]["duplication"]["duplicated_lines_pct"] > 3.0


def test_task_evaluator_bot_includes_local_quality_gates(tmp_path: Path) -> None:
    """Verify TaskEvaluatorBot runs LocalQualityGateBot and persists local_quality_gates in latest.json."""
    (tmp_path / "VERSION").write_text("0.1.0\n", encoding="utf-8")
    (tmp_path / "CHANGELOG.md").write_text("## [0.1.0] - 2026-10-31\n- Initial release\n", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "eval-demo"\n', encoding="utf-8")
    src = tmp_path / "src"
    src.mkdir()
    (src / "service.py").write_text("def run_service() -> str:\n    return 'ok'\n", encoding="utf-8")
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_service.py").write_text("def test_service() -> None:\n    assert True\n", encoding="utf-8")

    ev_bot = TaskEvaluatorBot(cwd=tmp_path)
    res = ev_bot.evaluate_task(
        task_id="issue-561",
        skip_tests=True,
        compound_node=False,
        sync_observability=False,
        dry_run=True,
    )
    assert "local_quality_gates" in res
    assert res["local_quality_gates"]["rule_id"] == "CR-LOCAL-QGATES-001"
    assert "local_quality_gates" in res["scorecard"]["tiers"]["deterministic"]["checks"]
    assert "Local Q-Gates (`thresholds.json`)" in res["scorecard_summary_markdown"]


def test_cli_quality_init_and_local_and_bot_registry(tmp_path: Path, monkeypatch) -> None:
    """Verify hath0r quality init, hath0r quality local, and BotRegistry local-quality-gate-bot."""
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "cli-qgate"\n', encoding="utf-8")
    src = tmp_path / "src"
    src.mkdir()
    (src / "mod.py").write_text("def hello() -> str:\n    return 'world'\n", encoding="utf-8")
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_mod.py").write_text("def test_mod() -> None:\n    assert True\n", encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    runner = CliRunner()

    init_res = runner.invoke(cli, ["quality", "init"])
    assert init_res.exit_code == 0
    assert (tmp_path / "thresholds.json").is_file()

    local_res = runner.invoke(cli, ["-o", "text", "quality", "local", "--all-files"])
    assert local_res.exit_code == 0
    assert "PASSED" in local_res.output

    reg = BotRegistry(cwd=tmp_path)
    assert "local-quality-gate-bot" in reg.registered_bot_ids()
    step = reg.invoke("local-quality-gate-bot", "evaluate", {"changed_only": False})
    assert step.success is True
