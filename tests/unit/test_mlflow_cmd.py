"""Unit tests for MLflow CLI commands and MLflowManagerBot."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from hath0r_cli.bots.mlflow_manager_bot import MLflowManagerBot, mlflow_manager_bot
from hath0r_cli.cccd.calibration_loop import CCCDCalibrationLoop
from hath0r_cli.cli import main


def test_mlflow_manager_bot_status_mocked():
    bot = MLflowManagerBot()
    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        status = bot.check_status(group="1-nation")
        assert status["healthy"] is True
        assert status["group"] == "1-nation"
        assert status["container"] == "1NMLFLOW"


def test_mlflow_manager_bot_get_experiments_mocked():
    bot = MLflowManagerBot()
    mock_payload = {
        "experiments": [
            {"experiment_id": "0", "name": "Default", "artifact_location": "/data/artifacts/0"},
            {"experiment_id": "1", "name": "cccd-calibration", "artifact_location": "/data/artifacts/1"},
        ]
    }
    with patch.object(bot, "_request", return_value=mock_payload):
        exps = bot.get_experiments(group="1-nation")
        assert len(exps) == 2
        assert exps[0]["name"] == "Default"
        assert exps[1]["name"] == "cccd-calibration"


def test_mlflow_manager_bot_log_run_mocked():
    bot = MLflowManagerBot()
    with patch.object(bot, "get_or_create_experiment", return_value="1"), patch.object(
        bot,
        "_request",
        side_effect=[
            {"run": {"info": {"run_id": "mock_run_12345"}}},  # create run
            {},  # log param
            {},  # log metric
            {},  # update status
        ],
    ):
        run_id = bot.log_run(
            experiment_name="cccd-calibration",
            run_name="unit_test_run",
            params={"temperature": 0.2},
            metrics={"loss": 0.05},
            group="1-nation",
        )
        assert run_id == "mock_run_12345"


def test_mlflow_cli_status():
    runner = CliRunner()
    result = runner.invoke(main, ["mlflow", "status", "--group", "1-nation"])
    assert result.exit_code == 0
    assert "MLflow Experiment Tracking Status" in result.output

    json_res = runner.invoke(main, ["mlflow", "status", "--group", "1-nation", "--json"])
    assert json_res.exit_code == 0
    parsed = json.loads(json_res.output)
    assert parsed["group"] == "1-nation"
    assert parsed["container"] == "1NMLFLOW"


def test_mlflow_cli_experiments():
    runner = CliRunner()
    with patch.object(
        mlflow_manager_bot,
        "get_experiments",
        return_value=[
            {"experiment_id": "1", "name": "cccd-calibration", "artifact_location": "/data/artifacts/1", "lifecycle_stage": "active"}
        ],
    ):
        result = runner.invoke(main, ["mlflow", "experiments", "--group", "1-nation"])
        assert result.exit_code == 0
        assert "cccd-calibration" in result.output

        json_res = runner.invoke(main, ["mlflow", "experiments", "--group", "1-nation", "--json"])
        assert json_res.exit_code == 0
        parsed = json.loads(json_res.output)
        assert len(parsed) == 1
        assert parsed[0]["name"] == "cccd-calibration"


def test_mlflow_cli_runs():
    runner = CliRunner()
    mock_runs = [
        {
            "info": {
                "run_id": "abcd1234efgh5678",
                "run_name": "test_run_1",
                "status": "FINISHED",
                "artifact_uri": "/data/artifacts/1/abcd",
            }
        }
    ]
    with patch.object(mlflow_manager_bot, "get_runs", return_value=mock_runs):
        result = runner.invoke(main, ["mlflow", "runs", "-e", "1", "--group", "1-nation"])
        assert result.exit_code == 0
        assert "test_run_1" in result.output

        json_res = runner.invoke(main, ["mlflow", "runs", "-e", "1", "--group", "1-nation", "--json"])
        assert json_res.exit_code == 0
        parsed = json.loads(json_res.output)
        assert len(parsed) == 1
        assert parsed[0]["info"]["run_id"] == "abcd1234efgh5678"


def test_mlflow_cli_log():
    runner = CliRunner()
    with patch.object(mlflow_manager_bot, "log_run", return_value="logged_run_999"):
        result = runner.invoke(
            main,
            [
                "mlflow",
                "log",
                "-e",
                "cccd-calibration",
                "-n",
                "cli_test",
                "-p",
                "temperature=0.3",
                "-m",
                "mean_snr_db=25.0",
                "--group",
                "1-nation",
            ],
        )
        assert result.exit_code == 0
        assert "logged_run_999" in result.output


def test_cccd_calibration_loop_mlflow_hook():
    loop = CCCDCalibrationLoop()
    with patch.object(mlflow_manager_bot, "log_run", return_value="mlflow_calib_run_77"):
        run_id = loop._log_to_mlflow(
            signature_name="test_signature",
            iterations=2,
            optimal_params={"temperature": 0.1},
            taguchi_res={"mean_snr_db": 30.5, "mean_quality_loss": 0.002},
            drift_metrics={"accuracy_drift": 0.001, "latency_drift_ms": 2.0},
            calibration_run=10,
        )
        assert run_id == "mlflow_calib_run_77"
