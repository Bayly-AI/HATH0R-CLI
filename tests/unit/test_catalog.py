"""Unit tests for catalog parsing/validation."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from hath0r_cli.catalog import CatalogError, parse_catalog


def test_parse_requires_control_tower_path(tmp_path: Path) -> None:
    path = tmp_path / "c.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "group_id": "g",
                "products": [
                    {
                        "product_id": "hath0r-cli",
                        "product_name": "CLI",
                        "role": "control-tower",
                        "canonical": True,
                        "is_control_tower": True,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(CatalogError) as exc:
        parse_catalog(path)
    assert exc.value.code == "PRODUCT_CATALOG_INVALID"
    assert "control_tower_path" in exc.value.message


def test_parse_missing_product_field(tmp_path: Path) -> None:
    path = tmp_path / "c.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "group_id": "g",
                "control_tower_path": "/t",
                "products": [
                    {
                        "product_id": "x",
                        "product_name": "X",
                        "role": "r",
                        "canonical": True,
                        # missing is_control_tower
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(CatalogError) as exc:
        parse_catalog(path)
    assert "is_control_tower" in exc.value.message
