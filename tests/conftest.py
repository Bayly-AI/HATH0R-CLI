"""Shared fixtures for HATH0R-CLI tests (hermetic tmp groups only)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

FRAMEWORK_SCHEMAS = Path("/Users/raybayly/Development/OpenSource/hath0r/lib/schemas")


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def framework_schemas() -> Path:
    return FRAMEWORK_SCHEMAS


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


@pytest.fixture
def mock_group_root(tmp_path: Path) -> Path:
    """Complete OpenSource group layout sufficient for doctor + catalog."""
    group = tmp_path / "OpenSource"
    group.mkdir()
    _write(group / "AGENTS.md", "group: hath0r-opensource\n")
    _write(group / "WARP.md", "policy\n")
    (group / ".hath0r" / "knowledgebase" / "catalogs").mkdir(parents=True)

    tower = str(group / "HATH0R-CLI")
    products = {
        "group_id": "hath0r-opensource",
        "products": [
            {
                "product_id": "hath0r-cli",
                "product_name": "HATH0R CLI",
                "role": "control-tower",
                "canonical": True,
                "is_control_tower": True,
            },
            {
                "product_id": "hath0r-framework",
                "product_name": "HATHOR Framework",
                "role": "framework",
                "canonical": True,
                "is_control_tower": False,
            },
            {
                "product_id": "hath0r-poc",
                "product_name": "HATHOR POC",
                "role": "poc",
                "canonical": True,
                "is_control_tower": False,
            },
        ],
    }
    hub = {
        "group_id": "hath0r-opensource",
        "control_tower_path": tower,
        "products": products["products"],
    }
    _write(
        group / ".hath0r" / "knowledgebase" / "catalogs" / "suite-products.yaml",
        yaml.safe_dump(hub),
    )

    cli_root = group / "HATH0R-CLI"
    (cli_root / "cfg").mkdir(parents=True)
    _write(cli_root / "AGENTS.md", "HATH0R-CLI\n")
    _write(
        cli_root / "cfg" / "control-tower.yaml",
        f"remote: Bayly-AI/HATH0R-CLI\nlocal_path: {tower}\n",
    )
    _write(
        cli_root / "cfg" / "suite.yaml",
        f"control_tower_path: {tower}\nproduct_id: hath0r-cli\n",
    )
    _write(
        cli_root / "cfg" / "knowledge-tower.yaml",
        f"is_control_tower: true\ncontrol_tower_path: {tower}\n",
    )
    _write(cli_root / "cfg" / "products.yaml", yaml.safe_dump(products))

    for name, product_id in (("hath0r", "hath0r-framework"), ("hath0r-poc", "hath0r-poc")):
        member = group / name
        (member / "cfg").mkdir(parents=True)
        _write(member / "AGENTS.md", "HATH0R-CLI control tower\n")
        _write(
            member / "cfg" / "knowledge-tower.yaml",
            f"is_control_tower: false\ncontrol_tower_path: {tower}\n",
        )
        _write(
            member / "cfg" / "suite.yaml",
            f"control_tower_path: {tower}\nproduct_id: {product_id}\n",
        )
    return group


@pytest.fixture
def mock_kb(tmp_path: Path) -> Path:
    """KB directory with a valid suite-products catalog."""
    kb = tmp_path / "kb"
    catalogs = kb / "catalogs"
    catalogs.mkdir(parents=True)
    hub = {
        "group_id": "hath0r-opensource",
        "control_tower_path": "/mock/HATH0R-CLI",
        "products": [
            {
                "product_id": "hath0r-cli",
                "product_name": "HATH0R CLI",
                "role": "control-tower",
                "canonical": True,
                "is_control_tower": True,
            },
            {
                "product_id": "hath0r-poc",
                "product_name": "HATHOR POC",
                "role": "poc",
                "canonical": True,
                "is_control_tower": False,
            },
        ],
    }
    (catalogs / "suite-products.yaml").write_text(yaml.safe_dump(hub), encoding="utf-8")
    return kb


@pytest.fixture
def mock_catalog(mock_kb: Path) -> Path:
    return mock_kb / "catalogs" / "suite-products.yaml"
