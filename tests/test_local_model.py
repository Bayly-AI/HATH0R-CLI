"""Unit tests for LocalModelBot and local CLI subcommands."""

from click.testing import CliRunner

from hath0r_cli.bots.local_model import LocalModelBot, LocalRuntimeStatus
from hath0r_cli.cli import main


def test_detect_hardware():
    bot = LocalModelBot()
    status = bot.detect_hardware()
    assert isinstance(status, LocalRuntimeStatus)
    assert status.os_name != ""
    assert isinstance(status.installed_models, list)


def test_generate_simulated_fallback():
    bot = LocalModelBot(ollama_url="http://127.0.0.1:59999")
    res = bot.generate(prompt="Hello local model", model="qwen2.5:7b")
    assert res["status"] in ("simulated", "success")
    assert "response" in res
    assert res["prompt_tokens"] > 0
    assert res["completion_tokens"] > 0


def test_cli_local_status():
    runner = CliRunner()
    result = runner.invoke(main, ["local", "status"])
    assert result.exit_code == 0
    assert "HATH0R Local Hardware & LLM Runtimes" in result.output
    assert "Operating System" in result.output


def test_cli_local_run():
    runner = CliRunner()
    result = runner.invoke(main, ["local", "run", "Summarize architectural policy", "-m", "llama3.2"])
    assert result.exit_code == 0
    assert "Model:" in result.output
    assert "Response:" in result.output
