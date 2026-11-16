"""Quote an order with the carbon rules."""

from typing import Dict, List

from msa_fixture.pricing import CARBON_RULES


def quote_carbon(subtotal: float, region: str) -> List[Dict[str, float]]:
    """Apply every carbon rule to a subtotal."""
    return [rule(subtotal, region) for rule in CARBON_RULES]
