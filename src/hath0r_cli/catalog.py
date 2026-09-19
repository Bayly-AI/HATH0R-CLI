"""Suite product catalog parsing and validation for kb.products."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


class CatalogError(Exception):
    """Catalog missing or invalid."""

    def __init__(self, code: str, message: str, remediation: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.remediation = remediation


PRODUCT_FIELDS = ("product_id", "product_name", "role", "canonical", "is_control_tower")


@dataclass
class CatalogResult:
    group_id: str
    control_tower_product_id: str
    products: list[dict[str, Any]]

    def to_data(self) -> dict[str, Any]:
        return {
            "group_id": self.group_id,
            "control_tower_product_id": self.control_tower_product_id,
            "products": list(self.products),
        }


def parse_catalog(path: Path) -> CatalogResult:
    """Load and validate the KB hub suite-products.yaml catalog.

    Derives control_tower_product_id from the single product with
    is_control_tower: true. Strips non-documented product fields.
    """
    if not path.is_file():
        raise CatalogError(
            "PRODUCT_CATALOG_NOT_FOUND",
            "The suite products catalog is unavailable.",
            "Verify the knowledgebase path and run hath0r doctor.",
        )

    try:
        raw = path.read_text(encoding="utf-8")
        data = yaml.safe_load(raw)
    except Exception as exc:  # noqa: BLE001 — surface as catalog invalid
        raise CatalogError(
            "PRODUCT_CATALOG_INVALID",
            f"The suite products catalog could not be parsed: {exc}",
            "Fix YAML syntax in the hub suite-products.yaml catalog.",
        ) from exc

    if not isinstance(data, dict):
        raise CatalogError(
            "PRODUCT_CATALOG_INVALID",
            "The suite products catalog root must be a mapping.",
            "Ensure suite-products.yaml is a YAML object with group_id and products.",
        )

    group_id = data.get("group_id")
    if not isinstance(group_id, str) or not group_id.strip():
        raise CatalogError(
            "PRODUCT_CATALOG_INVALID",
            "Catalog is missing a valid group_id string.",
            "Add group_id to the hub suite-products.yaml catalog.",
        )

    # Hub catalog uses control_tower_path (not nested control_tower.product_id).
    if "control_tower_path" not in data:
        raise CatalogError(
            "PRODUCT_CATALOG_INVALID",
            "Catalog is missing control_tower_path.",
            "Add control_tower_path to the hub suite-products.yaml catalog.",
        )

    products_raw = data.get("products")
    if not isinstance(products_raw, list) or not products_raw:
        raise CatalogError(
            "PRODUCT_CATALOG_INVALID",
            "Catalog products must be a non-empty list.",
            "Add a products array to the hub suite-products.yaml catalog.",
        )

    products: list[dict[str, Any]] = []
    towers: list[str] = []
    for idx, item in enumerate(products_raw):
        if not isinstance(item, dict):
            raise CatalogError(
                "PRODUCT_CATALOG_INVALID",
                f"Catalog products[{idx}] must be a mapping.",
                "Fix product entries in suite-products.yaml.",
            )
        missing = [f for f in PRODUCT_FIELDS if f not in item]
        if missing:
            raise CatalogError(
                "PRODUCT_CATALOG_INVALID",
                f"Catalog products[{idx}] missing required fields: {', '.join(missing)}.",
                "Each product needs product_id, product_name, role, canonical, is_control_tower.",
            )
        pid = item["product_id"]
        if not isinstance(pid, str) or not pid.strip():
            raise CatalogError(
                "PRODUCT_CATALOG_INVALID",
                f"Catalog products[{idx}].product_id must be a non-empty string.",
                "Fix product_id values in suite-products.yaml.",
            )
        if not isinstance(item["product_name"], str) or not item["product_name"].strip():
            raise CatalogError(
                "PRODUCT_CATALOG_INVALID",
                f"Catalog products[{idx}].product_name must be a non-empty string.",
                "Fix product_name values in suite-products.yaml.",
            )
        if not isinstance(item["role"], str) or not item["role"].strip():
            raise CatalogError(
                "PRODUCT_CATALOG_INVALID",
                f"Catalog products[{idx}].role must be a non-empty string.",
                "Fix role values in suite-products.yaml.",
            )
        if not isinstance(item["canonical"], bool):
            raise CatalogError(
                "PRODUCT_CATALOG_INVALID",
                f"Catalog products[{idx}].canonical must be a boolean.",
                "Fix canonical flags in suite-products.yaml.",
            )
        if not isinstance(item["is_control_tower"], bool):
            raise CatalogError(
                "PRODUCT_CATALOG_INVALID",
                f"Catalog products[{idx}].is_control_tower must be a boolean.",
                "Fix is_control_tower flags in suite-products.yaml.",
            )
        if item["is_control_tower"]:
            towers.append(pid)
        products.append(
            {
                "product_id": item["product_id"],
                "product_name": item["product_name"],
                "role": item["role"],
                "canonical": item["canonical"],
                "is_control_tower": item["is_control_tower"],
            }
        )

    if len(towers) != 1:
        raise CatalogError(
            "PRODUCT_CATALOG_INVALID",
            f"Catalog must have exactly one is_control_tower product (found {len(towers)}).",
            "Mark exactly one product with is_control_tower: true.",
        )

    return CatalogResult(
        group_id=group_id.strip(),
        control_tower_product_id=towers[0],
        products=products,
    )
