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


def test_token_telemetry_cli_bot(tmp_path):
    """Verify TokenTelemetryCLIBot record, list, and histogram analytics."""
    from hath0r_cli.bots.token_telemetry_bot import TokenTelemetryCLIBot

    bot = TokenTelemetryCLIBot(cwd=tmp_path)
    assert bot.list_records() == []

    # Record 3 events
    r1 = bot.record(prompt="Short prompt", user_id="alice", tier="light")
    r2 = bot.record(prompt="Medium length prompt for standard task", user_id="alice", tier="standard")
    r3 = bot.record(
        prompt="Very long reasoning prompt requiring in-depth mathematical decomposition",
        user_id="bob",
        tier="reasoning",
    )

    assert r1["prompt_tokens"] > 0
    assert r2["prompt_tokens"] > r1["prompt_tokens"]
    assert r3["cost_usd"] > 0

    # List
    all_recs = bot.list_records()
    assert len(all_recs) == 3

    alice_recs = bot.list_records(user_id="alice")
    assert len(alice_recs) == 2

    # Histogram
    hist = bot.histogram(metric="prompt_tokens", bins_count=3)
    assert hist["total_records"] == 3
    assert hist["total_tokens"] > 0
    assert len(hist["bins"]) == 3
    assert "alice" in hist["user_distribution"]
    assert "bob" in hist["user_distribution"]


def test_finops_tokens_cli_commands(tmp_path):
    """Verify hath0r finops tokens record, list, and histogram CLI commands."""
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        # Record
        res_rec = runner.invoke(
            cli,
            [
                "-o",
                "text",
                "finops",
                "tokens",
                "record",
                "-p",
                "Analyze system performance and generate a histogram.",
                "-u",
                "raybayly",
                "-t",
                "standard",
            ],
        )
        assert res_rec.exit_code == 0
        assert "Token Telemetry Recorded" in res_rec.output
        assert "raybayly" in res_rec.output

        # List
        res_list = runner.invoke(
            cli,
            [
                "-o",
                "text",
                "finops",
                "tokens",
                "list",
            ],
        )
        assert res_list.exit_code == 0
        assert "Token Telemetry Records" in res_list.output
        assert "raybayly" in res_list.output

        # Histogram
        res_hist = runner.invoke(
            cli,
            [
                "-o",
                "text",
                "finops",
                "tokens",
                "histogram",
                "--metric",
                "prompt_tokens",
            ],
        )
        assert res_hist.exit_code == 0
        assert "FinOps Token Distribution Histogram" in res_hist.output
        assert "Histogram Bins" in res_hist.output

        # JSON Histogram
        res_json = runner.invoke(
            cli,
            [
                "-o",
                "json",
                "finops",
                "tokens",
                "histogram",
            ],
        )
        assert res_json.exit_code == 0
        payload = json.loads(res_json.output)
        assert payload["state"] == "ok"
        assert payload["data"]["total_records"] == 1

        # Test filtering options on list and histogram
        res_list_filter = runner.invoke(
            cli,
            [
                "-o",
                "json",
                "finops",
                "tokens",
                "list",
                "--user",
                "nonexistent_user",
            ],
        )
        assert res_list_filter.exit_code == 0
        assert json.loads(res_list_filter.output)["data"]["count"] == 0

        res_hist_filter = runner.invoke(
            cli,
            [
                "-o",
                "json",
                "finops",
                "tokens",
                "histogram",
                "--user",
                "raybayly",
                "--metric",
                "total_tokens",
            ],
        )
        assert res_hist_filter.exit_code == 0
        assert json.loads(res_hist_filter.output)["data"]["total_records"] == 1


def test_local_model_bot_and_voice_telemetry_capture(tmp_path):
    """Verify that LocalModelBot and AgentDialogueBot automatically record telemetry."""
    from hath0r_cli.bots.local_model_bot import LocalModelBot
    from hath0r_cli.bots.token_telemetry_bot import TokenTelemetryCLIBot
    from hath0r_cli.bots.voice_converse import AgentDialogueBot

    # 1. LocalModelBot reason and generate_code
    local_bot = LocalModelBot(cwd=tmp_path)
    res_reason = local_bot.reason("Analyze security risks", force_offline=True)
    assert res_reason["success"] is True

    res_code = local_bot.generate_code("Write a parser", force_offline=True)
    assert res_code["success"] is True

    # 2. AgentDialogueBot reason
    voice_bot = AgentDialogueBot(cwd=tmp_path)
    res_voice = voice_bot.reason("Hello Hath0r status", dry_run=True)
    assert res_voice["success"] is True

    # 3. Check telemetry ledger
    telemetry = TokenTelemetryCLIBot(cwd=tmp_path)
    records = telemetry.list_records(limit=10)
    assert len(records) == 3

    agents = {r.get("agent_id") for r in records}
    assert "local_deepseek-r1_bot" in agents
    assert "local_qwen2.5-coder_bot" in agents
    assert "voice_dialogue_bot" in agents
