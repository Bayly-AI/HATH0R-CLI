"""Quote an order with the importduty rules."""

from typing import Dict, List

from msa_fixture.pricing import IMPORTDUTY_RULES


def quote_importduty(subtotal: float, region: str) -> List[Dict[str, float]]:
    """Apply every importduty rule to a subtotal."""
    return [rule(subtotal, region) for rule in IMPORTDUTY_RULES]
