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
    assert "pytorch" in data["data"]


def test_vision_inspect_command():
    """Verify hath0r vision inspect command with device flag."""
    runner = CliRunner()
    with tempfile.TemporaryDirectory() as tmp_dir:
        img_path = _create_sample_png(Path(tmp_dir) / "test_img.png")

        res = runner.invoke(cli, ["vision", "inspect", str(img_path), "--device", "cpu"])
        assert res.exit_code == 0
        assert "Vision Inspection Completed" in res.output or "inspection" in res.output.lower()

        res_json = runner.invoke(cli, ["-o", "json", "vision", "inspect", str(img_path), "--device", "cpu"])
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

        res = runner.invoke(cli, ["vision", "ground", str(ui_path), "--target", "Submit Button", "--device", "cpu"])
        assert res.exit_code == 0
        assert "Element Grounded" in res.output or "submit button" in res.output.lower()


def test_vision_embed_command():
    """Verify hath0r vision embed command with device flag."""
    runner = CliRunner()
    with tempfile.TemporaryDirectory() as tmp_dir:
        img_path = _create_sample_png(Path(tmp_dir) / "embed_img.png")

        res = runner.invoke(cli, ["vision", "embed", str(img_path), "--device", "cpu"])
        assert res.exit_code == 0
        assert "Embedding Generated" in res.output or "embedding" in res.output.lower()


def test_vision_rerank_command():
    """Verify hath0r vision rerank command."""
    runner = CliRunner()
    res = runner.invoke(
        cli,
        [
            "-o",
            "text",
            "vision",
            "rerank",
            "-q",
            "Docker orchestration",
            "-c",
            "Docker swarm container deployment",
            "-c",
            "Baking chocolate cookies",
            "--device",
            "cpu",
        ],
    )
    assert res.exit_code == 0
    assert "Neural Reranking Completed" in res.output or "rerank" in res.output.lower()

    res_json = runner.invoke(
        cli,
        [
            "-o",
            "json",
            "vision",
            "rerank",
            "-q",
            "Docker orchestration",
            "-c",
            "Docker swarm container deployment",
            "-c",
            "Baking chocolate cookies",
        ],
    )
    assert res_json.exit_code == 0
    payload = json.loads(res_json.output)
    assert payload["state"] == "ok"
    assert len(payload["data"]["ranked_candidates"]) == 2


def test_vision_parse_doc_pixel_native():
    """Verify hath0r vision parse-doc --pixel-native command."""
    runner = CliRunner()
    with tempfile.TemporaryDirectory() as tmp_dir:
        doc_path = _create_sample_png(Path(tmp_dir) / "balance_sheet_q3.png")

        res = runner.invoke(cli, ["-o", "text", "vision", "parse-doc", str(doc_path), "--pixel-native"])
        assert res.exit_code == 0
        assert "Pixel-Native 2D" in res.output
        assert "Extracted 2D Tables" in res.output

        res_json = runner.invoke(cli, ["-o", "json", "vision", "parse-doc", str(doc_path), "--pixel-native"])
        assert res_json.exit_code == 0
        payload = json.loads(res_json.output)
        assert payload["data"]["document_structure"]["pixel_native"] is True
        assert len(payload["data"]["document_structure"]["tables"]) > 0


def test_vision_ground_playwright():
    """Verify hath0r vision ground --playwright command."""
    runner = CliRunner()
    with tempfile.TemporaryDirectory() as tmp_dir:
        ui_path = _create_sample_png(Path(tmp_dir) / "sap_checkout.png")

        res = runner.invoke(
            cli,
            [
                "-o",
                "text",
                "vision",
                "ground",
                str(ui_path),
                "--target",
                "Approve PO Button",
                "--playwright",
                "--action",
                "click",
            ],
        )
        assert res.exit_code == 0
        assert "Playwright Action" in res.output
        assert "DOM-independent step ready" in res.output

        res_json = runner.invoke(
            cli,
            [
                "-o",
                "json",
                "vision",
                "ground",
                str(ui_path),
                "--target",
                "Approve PO Button",
                "--playwright",
            ],
        )
        assert res_json.exit_code == 0
        payload = json.loads(res_json.output)
        step = payload["data"]["playwright_step"]
        assert step["action"] == "click"
        assert "coordinates" in step
        assert step["coordinates"]["x"] > 0

