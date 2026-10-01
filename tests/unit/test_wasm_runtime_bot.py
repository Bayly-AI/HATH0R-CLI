"""Unit tests for WasmRuntimeBot and hath0r wasm CLI commands."""

from pathlib import Path
from click.testing import CliRunner

from hath0r_cli.cli import main as cli
from hath0r_cli.bots.wasm_runtime_bot import WasmCapabilities, WasmRuntimeBot


def test_wasm_module_validation(tmp_path: Path):
    """Verify validation of WASM magic header."""
    valid_wasm = tmp_path / "valid.wasm"
    # \x00asm followed by version 1 (\x01\x00\x00\x00)
    valid_wasm.write_bytes(b"\x00asm\x01\x00\x00\x00" + b"\x00" * 32)

    invalid_wasm = tmp_path / "invalid.wasm"
    invalid_wasm.write_bytes(b"NOT_A_WASM_FILE")

    bot = WasmRuntimeBot()
    res_valid = bot.validate_module(valid_wasm)
    assert res_valid["valid"] is True
    assert res_valid["wasm_version"] == 1

    res_invalid = bot.validate_module(invalid_wasm)
    assert res_invalid["valid"] is False
    assert "Invalid WASM" in res_invalid["error"]


def test_wasm_capability_execution(tmp_path: Path):
    """Verify execution with capabilities."""
    wasm_file = tmp_path / "agent_tool.wasm"
    wasm_file.write_bytes(b"\x00asm\x01\x00\x00\x00" + b"\x01\x04\x01\x60\x00\x00")

    bot = WasmRuntimeBot()
    caps = WasmCapabilities(
        allow_read=["/tmp/data"],
        allow_write=["/tmp/out"],
        max_memory_mb=32,
        fuel_limit=50_000_000,
    )
    res = bot.execute_module(wasm_file, capabilities=caps)
    assert res["success"] is True
    assert res["memory_used_mb"] <= 32
    assert res["fuel_consumed"] <= 50_000_000
    assert res["capabilities_granted"]["allow_read"] == ["/tmp/data"]


def test_cli_wasm_commands(tmp_path: Path):
    """Verify hath0r wasm status, validate, run commands."""
    wasm_file = tmp_path / "calc.wasm"
    wasm_file.write_bytes(b"\x00asm\x01\x00\x00\x00" + b"\x00" * 16)

    runner = CliRunner()
    res_status = runner.invoke(cli, ["-o", "json", "wasm", "status"])
    assert res_status.exit_code == 0
    assert "strict_deny_by_default" in res_status.output

    res_val = runner.invoke(cli, ["-o", "json", "wasm", "validate", str(wasm_file)])
    assert res_val.exit_code == 0
    assert "valid" in res_val.output

    res_run = runner.invoke(cli, ["-o", "json", "wasm", "run", str(wasm_file), "--allow-read", "/tmp"])
    assert res_run.exit_code == 0
    assert "fuel_consumed" in res_run.output
