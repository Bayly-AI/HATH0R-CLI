"""Quote an order with the bundle rules."""

from typing import Dict, List

from msa_fixture.pricing import BUNDLE_RULES


def quote_bundle(subtotal: float, region: str) -> List[Dict[str, float]]:
    """Apply every bundle rule to a subtotal."""
    return [rule(subtotal, region) for rule in BUNDLE_RULES]
