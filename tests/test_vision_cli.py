"""CLI tests for hath0r vision commands and subcommands."""

import json
import struct
import tempfile
from pathlib import Path
from click.testing import CliRunner

from hath0r_cli.cli import main as cli


def _create_sample_png(file_path: Path, width: int = 200, height: int = 150) -> Path:
    """Create a minimal valid PNG file for CLI testing."""
    signature = b"\x89PNG\r\n\x1a\n"
    ihdr_data = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    ihdr_crc = struct.pack(">I", 0)
    ihdr_chunk = struct.pack(">I", len(ihdr_data)) + b"IHDR" + ihdr_data + ihdr_crc
    file_path.write_bytes(signature + ihdr_chunk)
    return file_path


def test_vision_doctor_command():
    """Verify hath0r vision doctor text and JSON output."""
    runner = CliRunner()

    res_text = runner.invoke(cli, ["vision", "doctor"])
    assert res_text.exit_code == 0
    assert "HATH0R Vision Diagnostics" in res_text.output or "vision" in res_text.output.lower()

    res_json = runner.invoke(cli, ["-o", "json", "vision", "doctor"])
    assert res_json.exit_code == 0
    data = json.loads(res_json.output)
    assert data["state"] == "ok"
    assert data["data"]["operation"] == "doctor"


def test_vision_inspect_command():
    """Verify hath0r vision inspect command."""
    runner = CliRunner()
    with tempfile.TemporaryDirectory() as tmp_dir:
        img_path = _create_sample_png(Path(tmp_dir) / "test_img.png")

        res = runner.invoke(cli, ["vision", "inspect", str(img_path)])
        assert res.exit_code == 0
        assert "Vision Inspection Completed" in res.output or "inspection" in res.output.lower()

        res_json = runner.invoke(cli, ["-o", "json", "vision", "inspect", str(img_path)])
        assert res_json.exit_code == 0
        payload = json.loads(res_json.output)
        assert payload["data"]["success"] is True
        assert payload["data"]["image_metadata"]["width"] == 200


def test_vision_parse_doc_command():
    """Verify hath0r vision parse-doc command."""
    runner = CliRunner()
    with tempfile.TemporaryDirectory() as tmp_dir:
        doc_path = _create_sample_png(Path(tmp_dir) / "system_arch_diagram.png")

        res = runner.invoke(cli, ["vision", "parse-doc", str(doc_path)])
        assert res.exit_code == 0
        assert "Document Layout Parsed" in res.output or "diagram" in res.output.lower()


def test_vision_ground_command():
    """Verify hath0r vision ground command."""
    runner = CliRunner()
    with tempfile.TemporaryDirectory() as tmp_dir:
        ui_path = _create_sample_png(Path(tmp_dir) / "ui_mock.png")

        res = runner.invoke(cli, ["vision", "ground", str(ui_path), "--target", "Submit Button"])
        assert res.exit_code == 0
        assert "Element Grounded" in res.output or "submit button" in res.output.lower()


def test_vision_embed_command():
    """Verify hath0r vision embed command."""
    runner = CliRunner()
    with tempfile.TemporaryDirectory() as tmp_dir:
        img_path = _create_sample_png(Path(tmp_dir) / "embed_img.png")

        res = runner.invoke(cli, ["vision", "embed", str(img_path)])
        assert res.exit_code == 0
        assert "Embedding Generated" in res.output or "embedding" in res.output.lower()
