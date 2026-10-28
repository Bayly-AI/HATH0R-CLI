"""Unit and integration tests for HATH0R-CLI CICCCDCT control plane, bot, commands, and FastMCP tools."""

import json
import time
from pathlib import Path

import pytest
from click.testing import CliRunner

from hath0r_cli.bots.cicccd_bot import CICCCDCTManagingBot
from hath0r_cli.cccd.training_coordinator import CCCDTTrainingCoordinator
from hath0r_cli.cli import main
from hath0r_cli.server.mcp_server import create_mcp_server


@pytest.fixture
def temp_workspace(tmp_path: Path) -> Path:
    # Relative to now: the CT gate treats training older than 168h as stale.
    recent = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() - 3600))
    hath0r_dir = tmp_path / ".hath0r"
    hath0r_dir.mkdir(parents=True, exist_ok=True)
    state = {
        "schema_version": "hath0r.cicccdct.state/1",
        "active_calibration": True,
        "last_run_timestamp": recent,
        "total_calibration_runs": 10,
        "current_parameters": {"temperature": 0.2, "max_tokens": 2048},
        "drift_metrics": {"accuracy_drift": 0.001, "latency_drift_ms": 1.5, "token_tax_drift": -0.01},
        "training": {
            "active_training": True,
            "total_training_runs": 2,
            "last_trained_timestamp": recent,
            "active_model_name": "reasoning_slm",
            "active_model_version": 1,
            "active_model_stage": "Production",
            "train_loss": 0.42,
            "eval_benchmark_reward": 0.91,
            "candidate_model_improvement": 0.05,
            "dataset_samples_count": 50,
        },
    }
    (hath0r_dir / "cccd_state.json").write_text(json.dumps(state, indent=2), encoding="utf-8")
    return tmp_path


def test_cccd_training_coordinator(temp_workspace: Path) -> None:
    coordinator = CCCDTTrainingCoordinator(workspace_root=temp_workspace)

    # Test dataset curation
    curation_res = coordinator.curate_dataset(min_reward=0.80)
    assert curation_res["samples_curated"] > 0
    assert Path(curation_res["dataset_path"]).is_file()
    assert curation_res["statistics"]["mean_reward"] >= 0.80

    # Test running training job
    job_res = coordinator.run_training_job(
        target="test_slm",
        method="lora",
        epochs=2,
    )
    assert job_res["status"] == "completed"
    assert job_res["target"] == "test_slm"
    assert job_res["metrics"]["promotable"] is True
    assert Path(job_res["model_artifact_uri"]).is_file()

    # Test promoting model
    promo_res = coordinator.promote_model("test_slm", version=1, stage="Production")
    assert promo_res["status"] == "SUCCESS"
    assert promo_res["stage"] == "Production"


def test_cicccdct_managing_bot(temp_workspace: Path) -> None:
    bot = CICCCDCTManagingBot(root_dir=str(temp_workspace))

    # Test status
    status = bot.status()
    assert "training" in status
    assert status["training"]["active_model_name"] == "reasoning_slm"

    # Test validation
    val = bot.validate_cicccd()
    assert "ci" in val
    assert "cc" in val
    assert "cd" in val
    assert "ct" in val
    assert val["ct"]["active_model_name"] == "reasoning_slm"
    assert val["ct"]["eval_benchmark_reward"] >= 0.85
    assert val["ct"]["sla_compliant"] is True


def test_cicccdct_cli_commands(temp_workspace: Path, monkeypatch) -> None:
    runner = CliRunner()
    monkeypatch.chdir(temp_workspace)

    # Test status
    result = runner.invoke(main, ["-o", "text", "cicccdct", "status"])
    assert result.exit_code == 0
    assert "CIC³DCT / CIC{qubed}DCT" in result.output

    # Test cic3dct and cicqubedct aliases
    res_alias1 = runner.invoke(main, ["-o", "text", "cic3dct", "status"])
    assert res_alias1.exit_code == 0
    assert "CIC³DCT / CIC{qubed}DCT" in res_alias1.output

    res_alias2 = runner.invoke(main, ["-o", "text", "cicqubedct", "status"])
    assert res_alias2.exit_code == 0
    assert "CIC³DCT / CIC{qubed}DCT" in res_alias2.output

    # Test validate
    result = runner.invoke(main, ["-o", "text", "cicccdct", "validate"])
    assert result.exit_code == 0
    assert "CIC³DCT Closed-Loop 4-Pillar Validation" in result.output
    assert "Continuous Training (CT):" in result.output

    # Test dataset curate
    result = runner.invoke(main, ["-o", "text", "cicccdct", "dataset", "curate", "--min-reward", "0.75"])
    assert result.exit_code == 0
    assert "Training Dataset Curated Successfully" in result.output

    # Test train run
    result = runner.invoke(main, ["-o", "text", "cicccdct", "train", "run", "--target", "test_model", "--epochs", "1"])
    assert result.exit_code == 0
    assert "Continuous Training Job Completed" in result.output
    assert "test_model" in result.output

    # Test model list and promote
    result = runner.invoke(main, ["-o", "text", "cicccdct", "model", "list"])
    assert result.exit_code == 0
    assert "MLflow Model Registry" in result.output

    result = runner.invoke(main, ["-o", "text", "cicccdct", "model", "promote", "-m", "test_model", "-v", "1", "-s", "Staging"])
    assert result.exit_code == 0
    assert "Model Successfully Promoted" in result.output


def test_fastmcp_cicccdct_tools(temp_workspace: Path, monkeypatch) -> None:
    monkeypatch.chdir(temp_workspace)
    mcp = create_mcp_server()

    # Find registered tools
    tool_names = [t.name for t in mcp._tool_manager.list_tools()]
    assert "hath0r_cicccdct_status" in tool_names
    assert "hath0r_cicccdct_validate" in tool_names
    assert "hath0r_cicccdct_train" in tool_names
    assert "hath0r_cicccdct_curate_dataset" in tool_names
    assert "hath0r_model_registry_promote" in tool_names
