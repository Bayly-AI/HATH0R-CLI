"""Unit and CLI tests for FinOps Tokenizer Tax bot and commands."""

import json

from click.testing import CliRunner

from hath0r_cli.bots.tokenizer_tax_bot import TokenizerTaxBot
from hath0r_cli.cli import main as cli


def test_tokenizer_tax_bot_script_classification():
    """Verify Unicode script detection and expansion factor calculations."""
    bot = TokenizerTaxBot()

    # Latin
    res_lat = bot.audit("Hello world, this is a standard English test.")
    assert res_lat["success"] is True
    assert res_lat["token_metrics"]["inflation_ratio"] == 1.0

    # Arabic
    res_ar = bot.audit("هتحور للذكاء الاصطناعي تقدم نماذج معالجة متقدمة")
    assert res_ar["success"] is True
    assert res_ar["token_metrics"]["inflation_ratio"] >= 3.0
    assert any(s["script"] == "ARABIC" for s in res_ar["script_breakdown"])

    # Vocab and VRAM calculation
    assert res_ar["vocab_vram_overhead"]["vocab_vram_gb"] == 4.19
    assert res_ar["vit_patch_budget"]["total_continuous_patches"] > 0


def test_finops_cli_command():
    """Verify hath0r finops tokenizer-tax command text and JSON output."""
    runner = CliRunner()

    res = runner.invoke(
        cli,
        [
            "-o",
            "text",
            "finops",
            "tokenizer-tax",
            "شركة هتحور للذكاء الاصطناعي تقدم حلول متقدمة",
        ],
    )
    assert res.exit_code == 0
    assert "FinOps Tokenizer Tax Audit Completed" in res.output
    assert "Unicode Script Distribution" in res.output
    assert "ARABIC" in res.output
    assert "Vocabulary Memory Overhead" in res.output
    assert "Continuous Visual Patch Budget" in res.output

    # JSON Output mode
    res_json = runner.invoke(
        cli,
        [
            "-o",
            "json",
            "finops",
            "tokenizer-tax",
            "Enterprise multilingual evaluation in English and Español.",
        ],
    )
    assert res_json.exit_code == 0
    payload = json.loads(res_json.output)
    assert payload["state"] == "ok"
    assert payload["data"]["success"] is True
    assert "vocab_vram_overhead" in payload["data"]
    assert "vit_patch_budget" in payload["data"]
