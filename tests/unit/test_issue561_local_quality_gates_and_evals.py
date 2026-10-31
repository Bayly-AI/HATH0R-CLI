"""Unit tests for Issue #561: Local Quality Gates (thresholds.json) & TaskEvaluatorBot integration."""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from hath0r_cli.bots.local_quality_gate_bot import (
    SONARCLOUD_CANONICAL_THRESHOLDS,
    LocalQualityGateBot,
    _detect_stack_key,
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

    # Reload existing thresholds.json and verify custom threshold merge
    persisted["thresholds"]["min_coverage_pct"] = 85.0
    t_file.write_text(json.dumps(persisted), encoding="utf-8")
    reloaded = bot.load_or_init_thresholds(tmp_path, create_if_missing=False)
    assert reloaded["thresholds"]["min_coverage_pct"] == 85.0


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

    # Second run should detect existing test files and not re-scaffold
    res_py_again = bot.ensure_supporting_system(py_repo, install_missing=False, scaffold_missing=True)
    assert res_py_again["scaffolded_files"] == []

    # 2. Node-TS repo without test/ directory
    ts_repo = tmp_path / "ts_repo"
    ts_repo.mkdir()
    (ts_repo / "package.json").write_text('{"name": "ts-repo"}', encoding="utf-8")
    (ts_repo / "tsconfig.json").write_text('{"compilerOptions": {}}', encoding="utf-8")
    (ts_repo / "src").mkdir()
    (ts_repo / "src" / "index.ts").write_text(
        "export function greet(name: string): string {\n"
        "  if (name && name.length > 0) {\n"
        "    return `hi ${name}`;\n"
        "  }\n"
        "  return 'hello';\n"
        "}\n",
        encoding="utf-8",
    )

    res_ts = bot.ensure_supporting_system(ts_repo, install_missing=False, scaffold_missing=True)
    assert res_ts["technology"] == "node-ts"
    assert (ts_repo / "thresholds.json").is_file()
    assert (ts_repo / "test" / "qgate.smoke.test.ts").is_file()
    eval_ts = bot.evaluate_local_gates(ts_repo, changed_only=False, auto_init=True)
    assert eval_ts["gates"]["complexity"]["functions_scanned"] >= 1

    # 3. Rust, Go, and Infra-Python stack detection
    rust_repo = tmp_path / "rust_repo"
    rust_repo.mkdir()
    (rust_repo / "Cargo.toml").write_text('[package]\nname = "demo"\n', encoding="utf-8")
    assert _detect_stack_key(rust_repo) == "rust"

    go_repo = tmp_path / "go_repo"
    go_repo.mkdir()
    (go_repo / "go.mod").write_text("module example.com/demo\n", encoding="utf-8")
    assert _detect_stack_key(go_repo) == "go"

    infra_repo = tmp_path / "infra_repo"
    infra_repo.mkdir()
    (infra_repo / "deploy" / "docker").mkdir(parents=True)
    assert _detect_stack_key(infra_repo) == "infra-python"


def test_coverage_xml_summary_and_lcov_parsing(tmp_path: Path) -> None:
    """Verify coverage gate parses coverage.xml, coverage-summary.json, and lcov.info."""
    bot = LocalQualityGateBot(cwd=tmp_path)

    # 1. coverage.xml
    (tmp_path / "coverage.xml").write_text('<coverage line-rate="0.9125"></coverage>', encoding="utf-8")
    assert bot._read_existing_coverage_pct(tmp_path) == 91.25
    (tmp_path / "coverage.xml").unlink()

    # 2. coverage/coverage-summary.json
    cov_dir = tmp_path / "coverage"
    cov_dir.mkdir()
    (cov_dir / "coverage-summary.json").write_text(
        json.dumps({"total": {"lines": {"pct": 86.4}}}),
        encoding="utf-8",
    )
    assert bot._read_existing_coverage_pct(tmp_path) == 86.4
    (cov_dir / "coverage-summary.json").unlink()

    # 3. coverage/lcov.info
    (cov_dir / "lcov.info").write_text("TN:\nLF:100\nLH:88\nend_of_record\n", encoding="utf-8")
    assert bot._read_existing_coverage_pct(tmp_path) == 88.0


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
        "        elif item == 0:\n"
        "            total += 0\n"
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


def test_cli_quality_init_local_ensure_all_and_bot_registry(tmp_path: Path, monkeypatch) -> None:
    """Verify hath0r quality init, local, ensure-all, and BotRegistry local-quality-gate-bot."""
    ws = tmp_path / "ws"
    ws.mkdir()
    repo_dir = ws / "hath0r-atc"
    repo_dir.mkdir()
    (repo_dir / "pyproject.toml").write_text('[project]\nname = "cli-qgate"\n', encoding="utf-8")
    src = repo_dir / "src"
    src.mkdir()
    (src / "mod.py").write_text("def hello() -> str:\n    return 'world'\n", encoding="utf-8")
    tests = repo_dir / "tests"
    tests.mkdir()
    (tests / "test_mod.py").write_text("def test_mod() -> None:\n    assert True\n", encoding="utf-8")

    monkeypatch.chdir(repo_dir)
    runner = CliRunner()

    init_res = runner.invoke(cli, ["-o", "text", "quality", "init"])
    assert init_res.exit_code == 0
    assert (repo_dir / "thresholds.json").is_file()

    local_res = runner.invoke(cli, ["-o", "text", "quality", "local", "--all-files"])
    assert local_res.exit_code == 0
    assert "PASSED" in local_res.output

    ensure_res = runner.invoke(cli, ["-o", "text", "quality", "ensure-all", "--workspace-root", str(ws)])
    assert ensure_res.exit_code == 0
    assert "1/1 PASSED" in ensure_res.output

    reg = BotRegistry(cwd=repo_dir)
    assert "local-quality-gate-bot" in reg.registered_bot_ids()
    assert reg.invoke("local-quality-gate-bot", "init", {}).success is True
    assert reg.invoke("local-quality-gate-bot", "init", {}, dry_run=True).success is True
    assert reg.invoke("local-quality-gate-bot", "evaluate", {"changed_only": False}).success is True
    assert reg.invoke("local-quality-gate-bot", "detect-technology", {}).success is True
    assert reg.invoke("local-quality-gate-bot", "ensure-all", {}, dry_run=True).success is True
    assert reg.invoke("local-quality-gate-bot", "unknown-action", {}).success is False


def test_recursive_repo_discovery_and_flutter_c_stacks(tmp_path: Path) -> None:
    """Verify recursive discovery across multi-tech repos (flutter-dart, c-native, sonar-project.properties)."""
    flutter_repo = tmp_path / "groupA" / "mobile-app"
    flutter_repo.mkdir(parents=True)
    (flutter_repo / ".git").mkdir()
    (flutter_repo / "pubspec.yaml").write_text("name: mobile_app\n", encoding="utf-8")
    (flutter_repo / "lib").mkdir()
    (flutter_repo / "lib" / "main.dart").write_text("void main() {}\n", encoding="utf-8")
    (flutter_repo / "test").mkdir()
    (flutter_repo / "test" / "widget_test.dart").write_text("void main() { /* main */ }\n", encoding="utf-8")

    c_repo = tmp_path / "groupB" / "native-tool"
    c_repo.mkdir(parents=True)
    (c_repo / ".git").mkdir()
    (c_repo / "Makefile").write_text("all:\n\t@echo ok\n", encoding="utf-8")
    (c_repo / "sonar-project.properties").write_text("sonar.sources=src\nsonar.tests=tests\n", encoding="utf-8")
    (c_repo / "src").mkdir()
    (c_repo / "src" / "main.c").write_text("int main(void) { return 0; }\n", encoding="utf-8")

    bot = LocalQualityGateBot(cwd=tmp_path)
    res = bot.ensure_all_repos(workspace_root=tmp_path, recursive=True)
    assert res["repos_count"] == 2
    assert res["passed_count"] == 2
    assert res["success"] is True
    techs = {item["repo_name"]: item["technology"] for item in res["results"]}
    assert techs["groupA/mobile-app"] == "flutter-dart"
    assert techs["groupB/native-tool"] == "c-native"
