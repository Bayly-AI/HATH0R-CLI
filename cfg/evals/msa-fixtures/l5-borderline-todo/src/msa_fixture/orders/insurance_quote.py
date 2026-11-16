"""Quote an order with the insurance rules."""

from typing import Dict, List

from msa_fixture.pricing import INSURANCE_RULES


def quote_insurance(subtotal: float, region: str) -> List[Dict[str, float]]:
    """Apply every insurance rule to a subtotal."""
    return [rule(subtotal, region) for rule in INSURANCE_RULES]
