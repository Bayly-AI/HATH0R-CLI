"""Unit tests for VisionBot multimodal perception and document understanding."""

import base64
import json
import struct
import tempfile
from pathlib import Path

from hath0r_cli.bots.vision_bot import VisionBot


def _create_sample_png(file_path: Path, width: int = 120, height: int = 80) -> Path:
    """Create a minimal valid 1x1 or 120x80 PNG file for testing."""
    # PNG signature + IHDR chunk
    signature = b"\x89PNG\r\n\x1a\n"
    ihdr_data = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    ihdr_crc = struct.pack(">I", 0)  # Dummy CRC for test header parsing
    ihdr_chunk = struct.pack(">I", len(ihdr_data)) + b"IHDR" + ihdr_data + ihdr_crc
    file_path.write_bytes(signature + ihdr_chunk)
    return file_path


def test_read_image_metadata():
    """Verify zero-dependency image header parsing."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp = Path(tmp_dir)
        png_file = _create_sample_png(tmp / "test_diagram.png", 640, 480)

        bot = VisionBot(cwd=tmp)
        meta = bot.read_image_metadata(png_file)

        assert meta["format"] == "png"
        assert meta["width"] == 640
        assert meta["height"] == 480
        assert meta["size_bytes"] > 0
        assert len(meta["sha256"]) == 64


def test_inspect_image():
    """Verify multimodal image inspection and scene summary."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp = Path(tmp_dir)
        img_file = _create_sample_png(tmp / "sample_architecture_diagram.png", 800, 600)

        bot = VisionBot(cwd=tmp)
        res = bot.inspect_image(img_file)

        assert res["success"] is True
        assert res["operation"] == "inspect"
        assert "description" in res
        assert len(res["detected_objects"]) > 0
        assert res["image_metadata"]["width"] == 800


def test_parse_document():
    """Verify structured layout and architecture diagram parsing."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp = Path(tmp_dir)
        doc_file = _create_sample_png(tmp / "hathor_system_architecture.png", 1024, 768)

        bot = VisionBot(cwd=tmp)
        res = bot.parse_document(doc_file)

        assert res["success"] is True
        assert res["operation"] == "parse_doc"
        assert res["document_structure"]["doc_type"] == "architecture_diagram"
        assert len(res["document_structure"]["sections"]) > 0


def test_ground_element():
    """Verify UI element coordinate localization and bounding box extraction."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp = Path(tmp_dir)
        ui_file = _create_sample_png(tmp / "ui_login_screen.png", 1920, 1080)

        bot = VisionBot(cwd=tmp)
        res = bot.ground_element(ui_file, target="Sign In with Google button")

        assert res["success"] is True
        assert res["operation"] == "ground"
        grounded = res["grounded_target"]
        assert grounded["found"] is True
        assert len(grounded["bounding_box"]) == 4
        assert "x" in grounded["center_coordinates"]
        assert "y" in grounded["center_coordinates"]


def test_embed_visual():
    """Verify 512-dimensional multimodal embedding generation."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp = Path(tmp_dir)
        img_file = _create_sample_png(tmp / "embedding_sample.png", 256, 256)

        bot = VisionBot(cwd=tmp)
        res = bot.embed_visual(img_file)

        assert res["success"] is True
        assert res["operation"] == "embed"
        embedding = res["embedding"]
        assert len(embedding) == 512
        assert isinstance(embedding[0], float)


def test_check_capabilities():
    """Verify vision runtime diagnostics check."""
    bot = VisionBot()
    res = bot.check_capabilities()

    assert res["success"] is True
    assert res["operation"] == "doctor"
    assert "local_ollama" in res
    assert "remote_credentials_configured" in res
