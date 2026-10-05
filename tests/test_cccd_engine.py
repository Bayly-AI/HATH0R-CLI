"""Unit tests for Continuous Calibration & Continuous Development (CCCD) Engine."""

from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from hath0r_cli.cccd import CCCDCalibrationLoop, DSPyCompilerBridge, TaguchiLossOptimizer
from hath0r_cli.cli import main


def test_taguchi_loss_optimizer(tmp_path: Path) -> None:
    optimizer = TaguchiLossOptimizer()
    factors = ["temp", "top_p"]
    levels = {"temp": [0.1, 0.2], "top_p": [0.9, 0.95]}
    responses = [[10.0, 12.0], [15.0, 14.0], [8.0, 9.0], [11.0, 10.0]]

    result = optimizer.optimize_parameters(
        factors=factors,
        levels=levels,
        responses_matrix=responses,
        array_type="L4",
        criterion="smaller_is_better",
        target_m=0.0,
        sensitivity_k=1.0,
    )

    assert result["success"] is True
    assert result["array_type"] == "L4"
    assert "optimal_parameters" in result
    assert "temp" in result["optimal_parameters"]


def test_dspy_compiler_bridge(tmp_path: Path) -> None:
    bridge = DSPyCompilerBridge(compiled_prompts_dir=tmp_path / "compiled")
    dataset = [{"input": "test prompt", "expected_output": "test answer"}]

    res = bridge.compile_signature("test_signature", dataset=dataset)
    assert res["success"] is True
    assert res["signature_name"] == "test_signature"
    assert Path(res["artifact_path"]).exists()

    loaded = bridge.load_compiled_signature("test_signature")
    assert loaded is not None
    assert loaded["signature_name"] == "test_signature"

    all_signatures = bridge.list_compiled_signatures()
    assert len(all_signatures) == 1


def test_calibration_loop(tmp_path: Path) -> None:
    loop = CCCDCalibrationLoop(
        cwd=tmp_path,
        state_file=tmp_path / "cccd_state.json",
        dspy_bridge=DSPyCompilerBridge(compiled_prompts_dir=tmp_path / "compiled"),
    )

    status = loop.get_status()
    assert status["success"] is True
    assert status["state"]["total_calibration_runs"] == 0

    run_res = loop.run_calibration(iterations=2, signature_name="test_run_sig")
    assert run_res["success"] is True
    assert run_res["calibration_id"] == 1

    updated_status = loop.get_status()
    assert updated_status["state"]["total_calibration_runs"] == 1


def test_cccd_cli_commands(tmp_path: Path, monkeypatch) -> None:
    runner = CliRunner()

    # Test status
    res_status = runner.invoke(main, ["cccd", "status"])
    assert res_status.exit_code == 0
    assert "Continuous Calibration" in res_status.output or "total_calibration_runs" in res_status.output

    # Test calibrate
    res_cal = runner.invoke(main, ["cccd", "calibrate", "--iterations", "1", "--signature", "cli_test_sig"])
    assert res_cal.exit_code == 0
    assert "Completed Successfully" in res_cal.output or "calibration_id" in res_cal.output

    # Test auto-tune
    res_at = runner.invoke(main, ["cccd", "auto-tune", "--interval", "100"])
    assert res_at.exit_code == 0
    assert "Active" in res_at.output or "active_calibration" in res_at.output


def test_cccd_freshness_check(tmp_path: Path) -> None:
    loop = CCCDCalibrationLoop(
        cwd=tmp_path,
        state_file=tmp_path / "cccd_state.json",
        dspy_bridge=DSPyCompilerBridge(compiled_prompts_dir=tmp_path / "compiled"),
    )

    # Initially missing timestamp -> stale
    freshness = loop.check_calibration_freshness(max_age_hours=24.0)
    assert freshness["is_fresh"] is False
    assert freshness["stale"] is True

    # Run calibration -> fresh
    loop.run_calibration(iterations=1)
    freshness_after = loop.check_calibration_freshness(max_age_hours=24.0)
    assert freshness_after["is_fresh"] is True
    assert freshness_after["stale"] is False
    assert freshness_after["age_hours"] is not None and freshness_after["age_hours"] < 1.0

    # Simulate old timestamp (>24h ago)
    state = loop.load_state()
    state["last_run_timestamp"] = "2020-01-01T00:00:00Z"
    loop.save_state(state)

    freshness_stale = loop.check_calibration_freshness(max_age_hours=24.0)
    assert freshness_stale["is_fresh"] is False
    assert freshness_stale["stale"] is True
    assert freshness_stale["age_hours"] > 24.0
