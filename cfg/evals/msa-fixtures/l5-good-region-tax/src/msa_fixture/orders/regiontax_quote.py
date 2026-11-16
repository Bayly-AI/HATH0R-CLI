"""Quote an order with the regiontax rules."""

from typing import Dict, List

from msa_fixture.pricing import REGIONTAX_RULES


def quote_regiontax(subtotal: float, region: str) -> List[Dict[str, float]]:
    """Apply every regiontax rule to a subtotal."""
    return [rule(subtotal, region) for rule in REGIONTAX_RULES]
