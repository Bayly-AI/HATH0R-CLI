"""Quote an order with the wholesale rules."""

from typing import Dict, List

from msa_fixture.pricing import WHOLESALE_RULES


def quote_wholesale(subtotal: float, region: str) -> List[Dict[str, float]]:
    """Apply every wholesale rule to a subtotal."""
    return [rule(subtotal, region) for rule in WHOLESALE_RULES]
