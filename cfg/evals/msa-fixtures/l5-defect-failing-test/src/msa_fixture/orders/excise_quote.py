"""Quote an order with the excise rules."""

from typing import Dict, List

from msa_fixture.pricing import EXCISE_RULES


def quote_excise(subtotal: float, region: str) -> List[Dict[str, float]]:
    """Apply every excise rule to a subtotal."""
    return [rule(subtotal, region) for rule in EXCISE_RULES]
