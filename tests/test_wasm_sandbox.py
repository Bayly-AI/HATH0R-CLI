"""Unit tests for WasmSandboxBot and WebAssembly CLI subcommands."""

import tempfile
from pathlib import Path

from click.testing import CliRunner

from hath0r_cli.bots.wasm_sandbox import WasmExecutionResult, WasmSandboxBot
from hath0r_cli.cli import main


def test_wasm_header_validation():
    bot = WasmSandboxBot()
    with tempfile.TemporaryDirectory() as tmpdir:
        # Valid wasm magic bytes (\x00asm)
        valid_wasm = Path(tmpdir) / "module.wasm"
        valid_wasm.write_bytes(b"\x00asm\x01\x00\x00\x00")
        assert bot.validate_wasm_header(valid_wasm) is True

        # Invalid file
        invalid_wasm = Path(tmpdir) / "bad.wasm"
        invalid_wasm.write_bytes(b"not a wasm binary")
        assert bot.validate_wasm_header(invalid_wasm) is False


def test_wasm_runner_missing_file():
    bot = WasmSandboxBot()
    res = bot.run("/nonexistent/file.wasm")
    assert isinstance(res, WasmExecutionResult)
    assert res.success is False
    assert res.error_message == "FileNotFound"


def test_wasm_runner_execution_and_simulation():
    bot = WasmSandboxBot()
    with tempfile.TemporaryDirectory() as tmpdir:
        wasm_file = Path(tmpdir) / "test.wasm"
        wasm_file.write_bytes(b"\x00asm\x01\x00\x00\x00")

        res = bot.run(
            wasm_path=wasm_file,
            args=["--arg1", "val1"],
            fuel_limit=10000,
            timeout_seconds=5.0,
        )
        assert res.success is True
        assert res.exit_code == 0
        assert "Executed: test.wasm" in res.stdout


def test_cli_wasm_info():
    runner = CliRunner()
    result = runner.invoke(main, ["wasm", "info"])
    assert result.exit_code == 0
    assert "HATH0R WebAssembly (WASI) Sandboxing" in result.output
    assert "WASI Support" in result.output


def test_cli_wasm_run():
    runner = CliRunner()
    with tempfile.TemporaryDirectory() as tmpdir:
        wasm_file = Path(tmpdir) / "tool.wasm"
        wasm_file.write_bytes(b"\x00asm\x01\x00\x00\x00")

        result = runner.invoke(main, ["wasm", "run", str(wasm_file), "--fuel", "5000"])
        assert result.exit_code == 0
        assert "Sandbox Execution Succeeded" in result.output
