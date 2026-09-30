"""Unit and integration tests for ChangeValidationBot and validation-factory."""

from pathlib import Path

from click.testing import CliRunner

from hath0r_cli.bots.change_validation import ChangeValidationBot
from hath0r_cli.cli import main
from hath0r_cli.factory_validation import validate_factory_file


def test_classify_changes_by_type(tmp_path: Path):
    bot = ChangeValidationBot(cwd=tmp_path)
    files = [
        "src/ui/dashboard.html",
        "styles/theme.css",
        "scripts/runner.py",
        "bin/setup.sh",
        "docs/guide.md",
        "cfg/settings.json",
        "binary.bin",
    ]
    classified = bot.classify_changes(files=files)

    assert "src/ui/dashboard.html" in classified["ui"]
    assert "styles/theme.css" in classified["ui"]
    assert "scripts/runner.py" in classified["script"]
    assert "bin/setup.sh" in classified["script"]
    assert "docs/guide.md" in classified["text"]
    assert "cfg/settings.json" in classified["text"]
    assert "binary.bin" in classified["other"]


def test_validate_ui_html(tmp_path: Path):
    bot = ChangeValidationBot(cwd=tmp_path)

    # Valid HTML
    valid_file = tmp_path / "valid.html"
    valid_file.write_text("<!DOCTYPE html><html><body><h1>Hello</h1></body></html>")
    res_valid = bot.validate_ui(["valid.html"])
    assert res_valid["passed"] is True

    # Invalid HTML with missing closing tag
    invalid_file = tmp_path / "invalid.html"
    invalid_file.write_text("<html><body><h1>Missing closing")
    res_invalid = bot.validate_ui(["invalid.html"])
    assert res_invalid["passed"] is False
    assert len(res_invalid["errors"]) > 0


def test_validate_script_python(tmp_path: Path):
    bot = ChangeValidationBot(cwd=tmp_path)

    # Valid Python script
    valid_py = tmp_path / "valid.py"
    valid_py.write_text("def test_fn():\n    return 42\n")
    res_valid = bot.validate_script(["valid.py"])
    assert res_valid["passed"] is True

    # Invalid Python syntax
    invalid_py = tmp_path / "invalid.py"
    invalid_py.write_text("def broken_syntax(:\n")
    res_invalid = bot.validate_script(["invalid.py"])
    assert res_invalid["passed"] is False
    assert "SyntaxError" in res_invalid["errors"][0]


def test_validate_text_json_yaml(tmp_path: Path):
    bot = ChangeValidationBot(cwd=tmp_path)

    # Valid JSON
    valid_json = tmp_path / "data.json"
    valid_json.write_text('{"name": "hath0r", "version": "1.0.0"}')
    res_json = bot.validate_text(["data.json"])
    assert res_json["passed"] is True

    # Invalid JSON
    invalid_json = tmp_path / "bad.json"
    invalid_json.write_text("{bad json")
    res_bad_json = bot.validate_text(["bad.json"])
    assert res_bad_json["passed"] is False


def test_validate_all_workflow(tmp_path: Path):
    bot = ChangeValidationBot(cwd=tmp_path)

    (tmp_path / "index.html").write_text("<html><body>App</body></html>")
    (tmp_path / "main.py").write_text("x = 10\n")
    (tmp_path / "README.md").write_text("# Project Docs\n")

    res = bot.validate_all(files=["index.html", "main.py", "README.md"])
    assert res["status"] == "valid"
    assert res["ready_for_announcement"] is True
    assert res["summary"]["total_files"] == 3


def test_cli_validate_change_command(tmp_path: Path):
    runner = CliRunner()
    file_path = tmp_path / "test_doc.md"
    file_path.write_text("# Test Markdown Document")

    result = runner.invoke(main, ["validate-change", str(file_path)])
    assert result.exit_code == 0
    assert "Running Change Validation Gate" in result.output
    assert "All changes verified successfully" in result.output


def test_validation_factory_manifest_schema():
    factory_path = Path("cfg/factories/validation-factory.yaml")
    res = validate_factory_file(factory_path)
    assert res.valid is True
    assert res.factory_id == "validation-factory"
