"""Quote an order with the fx rules."""

from typing import Dict, List

from msa_fixture.pricing import FX_RULES


def quote_fx(subtotal: float, region: str) -> List[Dict[str, float]]:
    """Apply every fx rule to a subtotal."""
    return [rule(subtotal, region) for rule in FX_RULES]
