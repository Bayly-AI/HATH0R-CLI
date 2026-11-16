#!/usr/bin/env python3
"""Generate the level-stratified MSA panel v2 fixtures (#612).

Writes ``cfg/evals/msa-fixtures/base-v2`` (a multi-module fixture repository) and one change directory per
new part, then ``cfg/evals/msa-panel.yaml`` (schema ``hath0r.evals.msa-panel/v2``). The script is
deterministic: re-running it reproduces the same files. Parts are designed so the reference quality of
a part does not depend on its level (good = 0.95, borderline = 0.85, drift defect = 0.60, broken
defect = 0.40), which lets the study read any level trend in measured minus reference as gauge
linearity rather than as a property of the parts.

Usage: python scripts/msa/gen_panel_v2.py [--root <repo root>]
"""

from __future__ import annotations

import argparse
import json
import shutil
import textwrap
from pathlib import Path
from typing import Dict, List

import yaml

REF = {"good": 0.95, "borderline": 0.85, "drift": 0.60, "broken": 0.40}


def d(s: str) -> str:
    return textwrap.dedent(s).lstrip("\n")


# ------------------------------------------------------------------------------------------- base
BASE_FILES: Dict[str, str] = {
    "src/msa_fixture/inventory/__init__.py": d('''
        """Inventory: items and the in-memory store."""

        from msa_fixture.inventory.models import Item
        from msa_fixture.inventory.store import Store

        __all__ = ["Item", "Store"]
        '''),
    "src/msa_fixture/inventory/models.py": d('''
        """Inventory data model."""

        from dataclasses import dataclass


        @dataclass
        class Item:
            """A stock-keeping unit held in the store."""

            sku: str
            name: str
            qty: int
            price: float

            def value(self) -> float:
                """Stock value of this item."""
                return self.qty * self.price
        '''),
    "src/msa_fixture/inventory/store.py": d('''
        """In-memory inventory store."""

        from typing import Dict, List

        from msa_fixture.inventory.models import Item


        class Store:
            """Holds items by SKU."""

            def __init__(self) -> None:
                self._items: Dict[str, Item] = {}

            def add(self, item: Item) -> None:
                """Add or replace an item."""
                self._items[item.sku] = item

            def get(self, sku: str) -> Item:
                """Return the item for ``sku``; raises KeyError when unknown."""
                return self._items[sku]

            def remove(self, sku: str) -> Item:
                """Remove and return the item for ``sku``."""
                return self._items.pop(sku)

            def items(self) -> List[Item]:
                """All items, sorted by SKU."""
                return [self._items[k] for k in sorted(self._items)]

            def total_value(self) -> float:
                """Total stock value."""
                return sum(i.value() for i in self._items.values())
        '''),
    "src/msa_fixture/orders/__init__.py": d('''
        """Orders placed against the inventory store."""

        from msa_fixture.orders.service import OrderService

        __all__ = ["OrderService"]
        '''),
    "src/msa_fixture/orders/service.py": d('''
        """Order placement."""

        from typing import Dict, List

        from msa_fixture.inventory.store import Store


        class OrderService:
            """Places orders and reserves stock."""

            def __init__(self, store: Store) -> None:
                self.store = store
                self.placed: List[Dict[str, object]] = []

            def place(self, sku: str, qty: int) -> Dict[str, object]:
                """Reserve ``qty`` of ``sku``; raises ValueError when stock is short."""
                if qty <= 0:
                    raise ValueError("quantity must be positive")
                item = self.store.get(sku)
                if item.qty < qty:
                    raise ValueError(f"only {item.qty} of {sku} in stock")
                item.qty -= qty
                order = {"id": len(self.placed) + 1, "sku": sku, "qty": qty, "amount": round(qty * item.price, 2)}
                self.placed.append(order)
                return order
        '''),
    "src/msa_fixture/api/__init__.py": d('''
        """Request handlers over the order service."""
        '''),
    "src/msa_fixture/api/handlers.py": d('''
        """JSON-style request handlers."""

        from typing import Any, Dict

        from msa_fixture.orders.service import OrderService


        def handle_place_order(service: OrderService, payload: Dict[str, Any]) -> Dict[str, Any]:
            """Validate a payload and place an order; errors become a 400 response."""
            sku = payload.get("sku")
            qty = payload.get("qty")
            if not isinstance(sku, str) or not isinstance(qty, int):
                return {"status": 400, "error": "sku (str) and qty (int) are required"}
            try:
                order = service.place(sku, qty)
            except (KeyError, ValueError) as exc:
                return {"status": 400, "error": str(exc)}
            return {"status": 201, "order": order}
        '''),
    "contracts/order.schema.json": json.dumps(
        {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "title": "Order",
            "type": "object",
            "required": ["id", "sku", "qty", "amount"],
            "properties": {
                "id": {"type": "integer"},
                "sku": {"type": "string"},
                "qty": {"type": "integer", "minimum": 1},
                "amount": {"type": "number"},
            },
        },
        indent=2,
    )
    + "\n",
    "tests/test_store.py": d('''
        from msa_fixture.inventory import Item, Store


        def _store() -> Store:
            s = Store()
            s.add(Item("a1", "bolt", 10, 0.5))
            s.add(Item("b2", "nut", 4, 0.25))
            return s


        def test_get_and_total() -> None:
            s = _store()
            assert s.get("a1").name == "bolt"
            assert s.total_value() == 6.0


        def test_remove() -> None:
            s = _store()
            assert s.remove("b2").sku == "b2"
            assert [i.sku for i in s.items()] == ["a1"]
        '''),
    "tests/test_orders.py": d('''
        import pytest

        from msa_fixture.inventory import Item, Store
        from msa_fixture.orders import OrderService


        def _svc() -> OrderService:
            s = Store()
            s.add(Item("a1", "bolt", 10, 0.5))
            return OrderService(s)


        def test_place_reserves_stock() -> None:
            svc = _svc()
            order = svc.place("a1", 4)
            assert order["amount"] == 2.0
            assert svc.store.get("a1").qty == 6


        def test_place_rejects_short_stock() -> None:
            with pytest.raises(ValueError):
                _svc().place("a1", 11)
        '''),
    "tests/test_api.py": d('''
        from msa_fixture.api.handlers import handle_place_order
        from msa_fixture.inventory import Item, Store
        from msa_fixture.orders import OrderService


        def test_handle_place_order() -> None:
            s = Store()
            s.add(Item("a1", "bolt", 10, 0.5))
            res = handle_place_order(OrderService(s), {"sku": "a1", "qty": 2})
            assert res["status"] == 201


        def test_handle_bad_payload() -> None:
            res = handle_place_order(OrderService(Store()), {"sku": 1})
            assert res["status"] == 400
        '''),
}

# --------------------------------------------------------------------------------- code generators
REGIONS = ["north", "south", "east", "west", "central", "coastal", "alpine", "metro", "rural", "island"]


def gen_rules(prefix: str, count: int, *, swallow_at: int = -1, todo_at: int = -1) -> str:
    """``count`` distinct small pricing rules; optionally one swallowed exception or one untracked TODO."""
    out = [f'"""{prefix.title()} rules generated for the MSA panel."""', "", "from typing import Dict", "", ""]
    for i in range(count):
        region = REGIONS[i % len(REGIONS)]
        rate = round(0.01 + 0.007 * i, 3)
        fee = round(0.5 + 0.25 * i, 2)
        cap = 50 + 5 * i
        lines = [
            f"def {prefix}_rule_{i}(subtotal: float, region: str) -> Dict[str, float]:",
            f'    """{prefix.title()} rule {i}: {rate:.3f} rate, {fee:.2f} fee in {region}, capped at {cap}."""',
            f"    {prefix}_amount_{i} = round(subtotal * {rate}, 2)",
            f'    if region == "{region}":',
            f"        {prefix}_amount_{i} = {prefix}_amount_{i} + {fee}",
            f"    {prefix}_capped_{i} = min({prefix}_amount_{i}, {cap})",
        ]
        if i == todo_at:
            lines.append(f"    # TODO: confirm the {region} cap with finance before the next release")
        if i == swallow_at:
            lines += [
                f"    {prefix}_ratio_{i} = 0.0",
                "    try:",
                f"        {prefix}_ratio_{i} = {prefix}_capped_{i} / subtotal",
                "    except Exception:",
                "        pass",
            ]
            lines.append(f'    return {{"rule": {i}, "amount": {prefix}_capped_{i}, "subtotal": subtotal, "ratio": {prefix}_ratio_{i}}}')
        else:
            lines.append(f'    return {{"rule": {i}, "amount": {prefix}_capped_{i}, "subtotal": subtotal}}')
        out += lines + ["", ""]
    out.append(f"{prefix.upper()}_RULES = [")
    out += [f"    {prefix}_rule_{i}," for i in range(count)]
    out.append("]")
    return "\n".join(out) + "\n"


def gen_rules_test(module: str, prefix: str, count: int, *, broken: bool = False) -> str:
    out = [f"from {module} import {prefix.upper()}_RULES", "", ""]
    for i in range(0, count, 3):
        expected = "-1.0" if broken and i == 0 else f"{prefix.upper()}_RULES[{i}](0.0, 'none')['amount']"
        out += [
            f"def test_{prefix}_rule_{i}_returns_amount() -> None:",
            f"    res = {prefix.upper()}_RULES[{i}](100.0, 'nowhere')",
            f"    assert res['rule'] == {i}",
            "    assert res['amount'] >= 0",
            f"    assert {prefix.upper()}_RULES[{i}](0.0, 'none')['amount'] == {expected}",
            "",
            "",
        ]
    return "\n".join(out).rstrip() + "\n"


def complex_function() -> str:
    return d('''
        """Shipping estimator with a deliberately tangled decision tree."""


        def shipping_cost(weight: float, region: str, express: bool, member: bool, fragile: bool) -> float:
            """Estimate shipping."""
            cost = 0.0
            if weight > 0:
                if region == "north":
                    if express:
                        if member:
                            cost = 5.0
                        else:
                            if fragile:
                                cost = 12.0
                            else:
                                cost = 9.0
                    else:
                        if member and fragile:
                            cost = 4.0
                        elif member or fragile:
                            cost = 6.0
                        else:
                            cost = 7.0
                else:
                    if express:
                        if weight > 10:
                            if fragile:
                                cost = 20.0
                            else:
                                cost = 15.0
                        else:
                            cost = 10.0
                    else:
                        for step in range(int(weight)):
                            if step % 2 == 0:
                                cost += 0.5
                            else:
                                if member:
                                    cost += 0.25
                                else:
                                    cost += 0.75
            return cost
        ''')


def duplicated_block(name: str) -> str:
    body = "\n".join(
        f"    total_line_value_{k} = order_lines[{k}] * unit_prices[{k}] if len(order_lines) > {k} else 0.0"
        for k in range(14)
    )
    return d(f'''
        """{name.title()} totals."""

        from typing import List


        def {name}_totals(order_lines: List[float], unit_prices: List[float]) -> float:
            """Sum line values for the first fourteen lines."""
        ''') + body + "\n    return sum(\n        [\n" + "".join(f"            total_line_value_{k},\n" for k in range(14)) + "        ]\n    )\n"


def version_files(version: str, *, changelog: bool = True, pyproject: bool = True) -> Dict[str, str]:
    files = {"VERSION": version + "\n"}
    if pyproject:
        files["pyproject.toml"] = d(f'''
            [project]
            name = "msa-fixture"
            version = "{version}"
            requires-python = ">=3.10"

            [tool.pytest.ini_options]
            testpaths = ["tests"]
            pythonpath = ["src"]

            [tool.ruff]
            line-length = 120

            [tool.ruff.lint]
            select = ["E", "F", "W"]
            ''')
    if changelog:
        files["CHANGELOG.md"] = d(f'''
            # Changelog

            ## [{version}] - 2026-11-16

            ### Changed
            - Panel v2 change.

            ## [0.1.0] - 2026-11-01

            ### Added
            - Initial calculator module.
            ''')
    return files


def docs(title: str, sections: int, *, todo: bool = False) -> str:
    out = [f"# {title}", ""]
    for s in range(sections):
        out += [f"## Section {s + 1}", "", f"The {title.lower()} section {s + 1} explains part {s + 1} of the fixture.", ""]
    if todo:
        out += ["TODO: add the deployment diagram once the ops review is done.", ""]
    return "\n".join(out)


# ------------------------------------------------------------------------------------------- parts
def parts() -> List[Dict[str, object]]:
    P: List[Dict[str, object]] = []

    def add(pid: str, level: str, kind: str, focus: str, files: Dict[str, str] | None = None, change: str | None = None) -> None:
        expected = "fail" if kind in ("drift", "broken") else "pass"
        P.append(
            {
                "id": pid,
                "level": level,
                "expected": expected,
                "kind": kind,
                "borderline": kind == "borderline",
                "focus": focus,
                "change": change or pid,
                "files": files,
            }
        )

    # L1 — trivial: docs, config, version only
    add("good-docs-readme", "L1", "good", "document calc usage in readme", change="good-docs-readme")
    add("good-config-file", "L1", "good", "add calc precision config", change="good-config-file")
    add("good-version-bump", "L1", "good", "release patch version bump changelog", version_files("0.1.1"), change="l1-good-version-bump")
    add("l1-good-architecture-doc", "L1", "good", "document fixture architecture", {"docs/architecture.md": docs("Architecture", 6)})
    add("l1-defect-version-no-changelog", "L1", "drift", "bump version", version_files("0.1.1", changelog=False))
    add("l1-defect-pyproject-drift", "L1", "drift", "release version changelog", version_files("0.1.1", pyproject=False))
    add("l1-defect-changelog-ahead", "L1", "drift", "changelog release notes", {"CHANGELOG.md": version_files("0.2.0")["CHANGELOG.md"]})
    add("l1-borderline-docs-todo", "L1", "borderline", "document operations runbook", {"docs/operations.md": docs("Operations", 4, todo=True)})

    # L2 — one function plus its test
    add("good-add-subtract", "L2", "good", "add subtract function to msa_fixture calc with test", change="good-add-subtract")
    add("good-add-multiply", "L2", "good", "add multiply function to msa_fixture calc with test", change="good-add-multiply")
    add("good-bugfix-divide-zero", "L2", "good", "fix divide by zero in msa_fixture calc", change="good-bugfix-divide-zero")
    add("good-docstring", "L2", "good", "clarify add docstring and test negative numbers", change="good-docstring")
    add("defect-failing-test", "L2", "broken", "change add implementation", change="defect-failing-test")
    add("defect-swallowed-exception", "L2", "broken", "add safe divide to calc", change="defect-swallowed-exception")
    add(
        "l2-defect-store-remove-bug",
        "L2",
        "broken",
        "store remove returns item",
        {"src/msa_fixture/inventory/store.py": BASE_FILES["src/msa_fixture/inventory/store.py"].replace("return self._items.pop(sku)", "return self._items[sku]")},
    )
    add("good-source-no-test", "L2", "borderline", "add negate function to calc", change="good-source-no-test")

    # L3 — several functions in one module
    add("good-larger-feature", "L3", "good", "add stats module mean variance range", change="good-larger-feature")
    add(
        "l3-good-shipping-rules",
        "L3",
        "good",
        "shipping rules module",
        {"src/msa_fixture/shipping.py": gen_rules("shipping", 8), "tests/test_shipping.py": gen_rules_test("msa_fixture.shipping", "shipping", 8)},
    )
    add(
        "l3-good-tax-rules",
        "L3",
        "good",
        "tax rules module",
        {"src/msa_fixture/tax.py": gen_rules("tax", 9), "tests/test_tax.py": gen_rules_test("msa_fixture.tax", "tax", 9)},
    )
    add(
        "l3-defect-swallowed-buried",
        "L3",
        "broken",
        "fees rules module",
        {"src/msa_fixture/fees.py": gen_rules("fees", 8, swallow_at=5), "tests/test_fees.py": gen_rules_test("msa_fixture.fees", "fees", 8)},
    )
    add(
        "l3-defect-complexity-hotspot",
        "L3",
        "broken",
        "shipping cost estimator",
        {"src/msa_fixture/estimator.py": complex_function(), "tests/test_estimator.py": "from msa_fixture.estimator import shipping_cost\n\n\ndef test_shipping_cost() -> None:\n    assert shipping_cost(1.0, 'north', True, True, False) == 5.0\n"},
    )
    add(
        "l3-defect-failing-test-buried",
        "L3",
        "broken",
        "levy rules module",
        {"src/msa_fixture/levy.py": gen_rules("levy", 8), "tests/test_levy.py": gen_rules_test("msa_fixture.levy", "levy", 8, broken=True)},
    )
    add("l3-borderline-no-tests", "L3", "borderline", "surcharge rules module", {"src/msa_fixture/surcharge.py": gen_rules("surcharge", 8)})
    add(
        "l3-borderline-todo",
        "L3",
        "borderline",
        "duty rules module",
        {"src/msa_fixture/duty.py": gen_rules("duty", 8, todo_at=3), "tests/test_duty.py": gen_rules_test("msa_fixture.duty", "duty", 8)},
    )

    # L4 — several modules or a public interface
    def l4(prefix: str, n: int, **kw: int) -> Dict[str, str]:
        return {
            f"src/msa_fixture/pricing/{prefix}.py": gen_rules(prefix, n, **kw),
            "src/msa_fixture/pricing/__init__.py": f'"""Pricing rules."""\n\nfrom msa_fixture.pricing.{prefix} import {prefix.upper()}_RULES\n\n__all__ = ["{prefix.upper()}_RULES"]\n',
            f"src/msa_fixture/orders/{prefix}_quote.py": d(f'''
                """Quote an order with the {prefix} rules."""

                from typing import Dict, List

                from msa_fixture.pricing import {prefix.upper()}_RULES


                def quote_{prefix}(subtotal: float, region: str) -> List[Dict[str, float]]:
                    """Apply every {prefix} rule to a subtotal."""
                    return [rule(subtotal, region) for rule in {prefix.upper()}_RULES]
                '''),
            f"src/msa_fixture/api/{prefix}_handler.py": d(f'''
                """Quote handler for the {prefix} rules."""

                from typing import Any, Dict

                from msa_fixture.orders.{prefix}_quote import quote_{prefix}


                def handle_{prefix}_quote(payload: Dict[str, Any]) -> Dict[str, Any]:
                    """Return a quote or a 400 response."""
                    subtotal = payload.get("subtotal")
                    if not isinstance(subtotal, (int, float)):
                        return {{"status": 400, "error": "subtotal is required"}}
                    return {{"status": 200, "lines": quote_{prefix}(float(subtotal), str(payload.get("region", "")))}}
                '''),
        }

    def l4_tests(prefix: str, n: int, broken: bool = False) -> Dict[str, str]:
        return {
            f"tests/test_{prefix}_rules.py": gen_rules_test(f"msa_fixture.pricing.{prefix}", prefix, n, broken=broken),
            f"tests/test_{prefix}_handler.py": d(f'''
                from msa_fixture.api.{prefix}_handler import handle_{prefix}_quote


                def test_{prefix}_handler_ok() -> None:
                    assert handle_{prefix}_quote({{"subtotal": 10.0}})["status"] == 200


                def test_{prefix}_handler_bad() -> None:
                    assert handle_{prefix}_quote({{}})["status"] == 400
                '''),
        }

    add("l4-good-discounts", "L4", "good", "discount pricing across orders and api", {**l4("discount", 24), **l4_tests("discount", 24)})
    add("l4-good-loyalty", "L4", "good", "loyalty pricing across orders and api", {**l4("loyalty", 26), **l4_tests("loyalty", 26)})
    add("l4-good-promo", "L4", "good", "promo pricing across orders and api", {**l4("promo", 25), **l4_tests("promo", 25)})
    add("l4-defect-swallowed-buried", "L4", "broken", "rebate pricing across orders and api", {**l4("rebate", 24, swallow_at=17), **l4_tests("rebate", 24)})
    add(
        "l4-defect-duplication",
        "L4",
        "broken",
        "order and invoice totals",
        {
            "src/msa_fixture/orders/totals.py": duplicated_block("order"),
            "src/msa_fixture/api/totals.py": duplicated_block("order").replace("Order totals", "Api totals"),
            "src/msa_fixture/inventory/totals.py": duplicated_block("order").replace("Order totals", "Inventory totals"),
            "tests/test_totals.py": "from msa_fixture.orders.totals import order_totals\n\n\ndef test_totals() -> None:\n    assert order_totals([1.0], [2.0]) == 2.0\n",
        },
    )
    add("l4-defect-failing-test", "L4", "broken", "bundle pricing across orders and api", {**l4("bundle", 24), **l4_tests("bundle", 24, broken=True)})
    add("l4-borderline-no-tests", "L4", "borderline", "seasonal pricing across orders and api", l4("seasonal", 24))
    add("l4-borderline-todo", "L4", "borderline", "clearance pricing across orders and api", {**l4("clearance", 24, todo_at=9), **l4_tests("clearance", 24)})

    # L5 — contracts or schemas across modules, large
    schema_v2 = json.loads(BASE_FILES["contracts/order.schema.json"])
    schema_v2["properties"]["currency"] = {"type": "string", "pattern": "^[A-Z]{3}$"}
    schema_v2["required"].append("currency")
    schema_text = json.dumps(schema_v2, indent=2) + "\n"

    def l5(prefix: str, n: int, **kw: int) -> Dict[str, str]:
        files = l4(prefix, n, **kw)
        files["contracts/order.schema.json"] = schema_text
        files[f"contracts/{prefix}-quote.schema.json"] = json.dumps(
            {"$schema": "https://json-schema.org/draft/2020-12/schema", "title": f"{prefix} quote", "type": "object", "required": ["rule", "amount"]}, indent=2
        ) + "\n"
        files[f"src/msa_fixture/inventory/{prefix}_stock.py"] = gen_rules(f"{prefix}stock", n // 2)
        return files

    def l5_tests(prefix: str, n: int, broken: bool = False) -> Dict[str, str]:
        t = l4_tests(prefix, n, broken)
        t[f"tests/test_{prefix}_stock.py"] = gen_rules_test(f"msa_fixture.inventory.{prefix}_stock", f"{prefix}stock", n // 2)
        return t

    add("l5-good-currency", "L5", "good", "currency in order contract with fx pricing", {**l5("fx", 40), **l5_tests("fx", 40), **version_files("0.2.0")})
    add("l5-good-region-tax", "L5", "good", "regional tax contract and pricing", {**l5("regiontax", 42), **l5_tests("regiontax", 42), **version_files("0.2.0")})
    add("l5-good-wholesale", "L5", "good", "wholesale contract and pricing", {**l5("wholesale", 41), **l5_tests("wholesale", 41), **version_files("0.2.0")})
    add("l5-defect-schema-version-drift", "L5", "drift", "freight contract and pricing", {**l5("freight", 40), **l5_tests("freight", 40), **version_files("0.2.0", changelog=False)})
    add("l5-defect-swallowed-buried", "L5", "broken", "import duty contract and pricing", {**l5("importduty", 40, swallow_at=31), **l5_tests("importduty", 40), **version_files("0.2.0")})
    add("l5-defect-failing-test", "L5", "broken", "excise contract and pricing", {**l5("excise", 40), **l5_tests("excise", 40, broken=True), **version_files("0.2.0")})
    add("l5-borderline-no-tests", "L5", "borderline", "carbon levy contract and pricing", {**l5("carbon", 40), **version_files("0.2.0")})
    add("l5-borderline-todo", "L5", "borderline", "insurance contract and pricing", {**l5("insurance", 40, todo_at=22), **l5_tests("insurance", 40), **version_files("0.2.0")})
    return P


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[2]))
    args = ap.parse_args()
    root = Path(args.root)
    fx = root / "cfg" / "evals" / "msa-fixtures"
    base_v2 = fx / "base-v2"
    if base_v2.exists():
        shutil.rmtree(base_v2)
    shutil.copytree(fx / "base", base_v2)
    (base_v2 / "pyproject.toml").write_text(version_files("0.1.0")["pyproject.toml"], encoding="utf-8")
    for rel, text in BASE_FILES.items():
        p = base_v2 / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")

    panel_parts = []
    for part in parts():
        files = part.pop("files")
        if files:
            cdir = fx / str(part["change"])
            if cdir.exists():
                shutil.rmtree(cdir)
            for rel, text in files.items():
                p = cdir / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(text, encoding="utf-8")
        kind = str(part.pop("kind"))
        part["base"] = "base-v2"
        part["reference"] = {"verdict": part["expected"], "quality": REF[kind], "kind": kind, "source": "author rubric (2 human reviewers pending, #611)"}
        panel_parts.append(part)

    panel = {
        "schema_version": "hath0r.evals.msa-panel/v2",
        "fixtures_root": "msa-fixtures",
        "levels": "cfg/evals/complexity-levels.yaml",
        "targets": {"max_grr_pct": 10.0, "min_ndc": 5, "max_level_bias": 0.02, "alpha": 0.05, "max_flip_rate": 0.05, "borderline_band": 0.05},
        "operators": [
            {"id": "evaluator-a"},
            {"id": "evaluator-b"},
            {"id": "variant", "variant": True},
        ],
        "parts": panel_parts,
    }
    header = (
        "# Level-stratified Gage R&R panel for the Hath0r eval pipeline (#612, epic #610).\n"
        "# Generated by scripts/msa/gen_panel_v2.py; edit the generator, not this file.\n"
        "# Each part is a fixture repository (base) plus a change (the diff the gauge judges), with a complexity\n"
        "# level (cfg/evals/complexity-levels.yaml) and a reference verdict and quality that do not depend on level.\n"
        "# Operators: two identical evaluator instances and a 'variant' operator that presents each change in a\n"
        "# meaning-preserving form (blank lines and top-level definition order), the gauge's real repeatability test.\n"
    )
    (root / "cfg" / "evals" / "msa-panel.yaml").write_text(header + yaml.safe_dump(panel, sort_keys=False, width=200), encoding="utf-8")
    print(f"wrote base-v2 and {len(panel_parts)} parts")


if __name__ == "__main__":
    main()
