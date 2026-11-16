"""Quote an order with the promo rules."""

from typing import Dict, List

from msa_fixture.pricing import PROMO_RULES


def quote_promo(subtotal: float, region: str) -> List[Dict[str, float]]:
    """Apply every promo rule to a subtotal."""
    return [rule(subtotal, region) for rule in PROMO_RULES]
