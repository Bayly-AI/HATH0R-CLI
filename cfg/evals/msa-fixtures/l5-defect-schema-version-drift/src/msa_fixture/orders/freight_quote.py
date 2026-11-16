"""Quote an order with the freight rules."""

from typing import Dict, List

from msa_fixture.pricing import FREIGHT_RULES


def quote_freight(subtotal: float, region: str) -> List[Dict[str, float]]:
    """Apply every freight rule to a subtotal."""
    return [rule(subtotal, region) for rule in FREIGHT_RULES]
