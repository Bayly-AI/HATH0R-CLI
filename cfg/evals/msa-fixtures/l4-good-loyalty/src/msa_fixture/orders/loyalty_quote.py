"""Quote an order with the loyalty rules."""

from typing import Dict, List

from msa_fixture.pricing import LOYALTY_RULES


def quote_loyalty(subtotal: float, region: str) -> List[Dict[str, float]]:
    """Apply every loyalty rule to a subtotal."""
    return [rule(subtotal, region) for rule in LOYALTY_RULES]
