"""Unit tests for CodeParser and code CLI commands."""

from pathlib import Path

from click.testing import CliRunner

from hath0r_cli.cli import main as cli
from hath0r_cli.code_parser import CodeParser


def test_python_ast_parsing():
    """Verify python class and function symbol extraction."""
    code = '''"""Sample module."""

class MyClass:
    """Class docstring."""
    def method_one(self, x: int) -> bool:
        """Method doc."""
        return True

def standalone_func(y: str):
    """Function doc."""
    pass
'''
    parser = CodeParser()
    symbols = parser.extract_symbols(code, language="python")
    assert len(symbols) == 2

    # Class check
    assert symbols[0].name == "MyClass"
    assert symbols[0].symbol_type == "class"
    assert symbols[0].docstring == "Class docstring."
    assert len(symbols[0].children) == 1
    assert symbols[0].children[0].name == "method_one"

    # Function check
    assert symbols[1].name == "standalone_func"
    assert symbols[1].symbol_type == "function"


def test_typescript_symbol_parsing():
    """Verify TypeScript interface and function extraction."""
    code = '''export interface UserProfile {
    id: string;
}

export async function fetchUser(id: string): Promise<UserProfile> {
    return { id };
}

export const helper = (val: number) => {
    return val * 2;
};
'''
    parser = CodeParser()
    symbols = parser.extract_symbols(code, language="typescript")
    assert len(symbols) == 3
    assert symbols[0].name == "UserProfile"
    assert symbols[0].symbol_type == "interface"
    assert symbols[1].name == "fetchUser"
    assert symbols[1].symbol_type == "function"
    assert symbols[2].name == "helper"


def test_generate_outline():
    """Verify outline skeleton generation."""
    code = '''class Worker:
    def run(self):
        print("heavy work")
'''
    parser = CodeParser()
    outline = parser.generate_outline(code, language="python")
    assert "class Worker:" in outline
    assert "def run(self):" in outline
    assert "..." in outline
    assert 'print("heavy work")' not in outline


def test_syntax_validation():
    """Verify syntax validation for python and bracket matching."""
    parser = CodeParser()
    valid_py = "def foo():\n    return 42\n"
    invalid_py = "def foo(\n return"

    ok, err = parser.validate_syntax(valid_py, "python")
    assert ok is True
    assert err is None

    bad_ok, bad_err = parser.validate_syntax(invalid_py, "python")
    assert bad_ok is False
    assert "SyntaxError" in bad_err

    # Bracket validation
    bad_ts = "function test() { if (true) { return; }"
    ts_ok, ts_err = parser.validate_syntax(bad_ts, "typescript")
    assert ts_ok is False


def test_code_cli_outline_and_symbols(tmp_path: Path):
    """Verify hath0r code outline and symbols CLI commands."""
    sample_file = tmp_path / "sample.py"
    sample_file.write_text("class Demo:\n    def execute(self):\n        pass\n")

    runner = CliRunner()
    res = runner.invoke(cli, ["-o", "text", "code", "outline", str(sample_file)])
    assert res.exit_code == 0
    assert "class Demo:" in res.output

    res_sym = runner.invoke(cli, ["-o", "json", "code", "symbols", str(sample_file)])
    assert res_sym.exit_code == 0
    assert "Demo" in res_sym.output
