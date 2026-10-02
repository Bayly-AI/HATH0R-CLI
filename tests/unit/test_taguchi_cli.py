"""Unit and CLI tests for Taguchi Robust Optimization bot and commands."""

import json
from click.testing import CliRunner

from hath0r_cli.cli import main as cli
from hath0r_cli.bots.taguchi_bot import TaguchiBot


def test_taguchi_bot_matrix_generation():
    """Verify orthogonal array generation across L4, L8, L9, L12, L18."""
    bot = TaguchiBot()

    # L9: 9 runs, 4 factors
    res_l9 = bot.generate_matrix(array_type="L9", factors=["temp", "top_p", "retrieval_k", "chunks"])
    assert res_l9["success"] is True
    assert res_l9["total_runs"] == 9
    assert len(res_l9["matrix"]) == 9
    assert res_l9["factors"] == ["temp", "top_p", "retrieval_k", "chunks"]

    # L4: 4 runs, 3 factors
    res_l4 = bot.generate_matrix(array_type="L4")
    assert res_l4["total_runs"] == 4
    assert len(res_l4["matrix"]) == 4

    # L18: 18 runs
    res_l18 = bot.generate_matrix(array_type="L18")
    assert res_l18["total_runs"] == 18


def test_taguchi_bot_snr_calculation():
    """Verify SNR calculations across criteria."""
    bot = TaguchiBot()

    # Smaller is better
    snr_small = bot.calculate_snr([10.0, 12.0, 11.0], criterion="smaller_is_better")
    assert isinstance(snr_small, float)
    assert snr_small < 0

    # Larger is better
    snr_large = bot.calculate_snr([95.0, 98.0, 92.0], criterion="larger_is_better")
    assert isinstance(snr_large, float)

    # Nominal is best
    snr_nom = bot.calculate_snr([50.0, 50.1, 49.9], criterion="nominal_is_best")
    assert snr_nom > 40.0


def test_taguchi_bot_quality_loss():
    """Verify quadratic loss function L(y) = k(y-m)^2."""
    bot = TaguchiBot()
    loss = bot.calculate_loss(measured_y=12.0, target_m=10.0, sensitivity_k=5.0)
    assert loss["deviation"] == 2.0
    assert loss["estimated_loss"] == 20.0


def test_taguchi_cli_command():
    """Verify hath0r optimize taguchi CLI execution."""
    runner = CliRunner()

    res = runner.invoke(
        cli,
        [
            "-o",
            "text",
            "optimize",
            "taguchi",
            "--array",
            "L9",
            "-f",
            "temp",
            "-f",
            "top_p",
            "--snr",
            "100.0,95.0,105.0",
            "--loss-k",
            "2.5",
            "--target-m",
            "100.0",
            "--measured-y",
            "104.0",
        ],
    )
    assert res.exit_code == 0
    assert "Taguchi Design Generated" in res.output
    assert "Orthogonal Array Matrix" in res.output
    assert "Signal-to-Noise Ratio (SNR)" in res.output
    assert "Estimated Quality Loss" in res.output

    # JSON Output mode
    res_json = runner.invoke(
        cli,
        [
            "-o",
            "json",
            "optimize",
            "taguchi",
            "--array",
            "L4",
        ],
    )
    assert res_json.exit_code == 0
    payload = json.loads(res_json.output)
    assert payload["state"] == "ok"
    assert payload["data"]["array_type"] == "L4"
    assert payload["data"]["total_runs"] == 4
