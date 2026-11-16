"""Quote an order with the discount rules."""

from typing import Dict, List

from msa_fixture.pricing import DISCOUNT_RULES


def quote_discount(subtotal: float, region: str) -> List[Dict[str, float]]:
    """Apply every discount rule to a subtotal."""
    return [rule(subtotal, region) for rule in DISCOUNT_RULES]
