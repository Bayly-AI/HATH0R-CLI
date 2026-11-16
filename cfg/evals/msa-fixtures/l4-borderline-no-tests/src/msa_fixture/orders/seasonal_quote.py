"""Quote an order with the seasonal rules."""

from typing import Dict, List

from msa_fixture.pricing import SEASONAL_RULES


def quote_seasonal(subtotal: float, region: str) -> List[Dict[str, float]]:
    """Apply every seasonal rule to a subtotal."""
    return [rule(subtotal, region) for rule in SEASONAL_RULES]
