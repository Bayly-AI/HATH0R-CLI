"""Quote an order with the rebate rules."""

from typing import Dict, List

from msa_fixture.pricing import REBATE_RULES


def quote_rebate(subtotal: float, region: str) -> List[Dict[str, float]]:
    """Apply every rebate rule to a subtotal."""
    return [rule(subtotal, region) for rule in REBATE_RULES]
