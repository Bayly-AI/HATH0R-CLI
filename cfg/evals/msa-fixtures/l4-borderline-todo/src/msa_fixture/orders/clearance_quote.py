"""Quote an order with the clearance rules."""

from typing import Dict, List

from msa_fixture.pricing import CLEARANCE_RULES


def quote_clearance(subtotal: float, region: str) -> List[Dict[str, float]]:
    """Apply every clearance rule to a subtotal."""
    return [rule(subtotal, region) for rule in CLEARANCE_RULES]
