"""Unit tests for LocalModelBot and hath0r local CLI commands."""

from click.testing import CliRunner

from hath0r_cli.cli import main as cli
from hath0r_cli.bots.local_model_bot import LocalModelBot, SUPPORTED_LOCAL_MODELS


def test_cot_splitting():
    """Verify regex separation of <think>...</think> from response text."""
    raw = "<think>\n1. Step A\n2. Step B\n</think>\nHere is the answer."
    cot, ans = LocalModelBot.split_cot(raw)
    assert "1. Step A" in cot
    assert "2. Step B" in cot
    assert ans == "Here is the answer."

    # When no <think> tag
    raw_no_cot = "Direct output without think."
    cot2, ans2 = LocalModelBot.split_cot(raw_no_cot)
    assert cot2 == ""
    assert ans2 == "Direct output without think."


def test_local_model_list():
    """Verify supported model registry."""
    bot = LocalModelBot()
    models = bot.list_models()
    assert len(models) >= 4
    assert any(m["model_id"] == "deepseek-r1:7b" for m in models)
    assert any(m["model_id"] == "qwen2.5-coder:7b" for m in models)


def test_local_reason_offline():
    """Verify offline deterministic reasoning."""
    bot = LocalModelBot()
    res = bot.reason("How do mutex locks avoid race conditions?", model="deepseek-r1:7b", force_offline=True)
    assert res["success"] is True
    assert "thinking_trace" in res
    assert "Analysis complete" in res["response"]


def test_local_code_offline():
    """Verify offline deterministic code generation."""
    bot = LocalModelBot()
    res = bot.generate_code("Build an LRU cache", model="qwen2.5-coder:7b", language="python", force_offline=True)
    assert res["success"] is True
    assert "def handle_task" in res["code"]


def test_cli_local_commands():
    """Verify hath0r local reason, code, and models CLI subcommands."""
    runner = CliRunner()

    res_models = runner.invoke(cli, ["-o", "json", "local", "models"])
    assert res_models.exit_code == 0
    assert "deepseek-r1:7b" in res_models.output

    res_reason = runner.invoke(cli, ["-o", "json", "local", "reason", "Test query", "--offline"])
    assert res_reason.exit_code == 0
    assert "thinking_trace" in res_reason.output

    res_code = runner.invoke(cli, ["-o", "json", "local", "code", "Test code task", "--offline"])
    assert res_code.exit_code == 0
    assert "code" in res_code.output
