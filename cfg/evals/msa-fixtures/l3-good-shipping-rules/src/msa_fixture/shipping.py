"""Shipping rules generated for the MSA panel."""

from typing import Dict


def shipping_rule_0(subtotal: float, region: str) -> Dict[str, float]:
    """Shipping rule 0: 0.010 rate, 0.50 fee in north, capped at 50."""
    shipping_amount_0 = round(subtotal * 0.01, 2)
    if region == "north":
        shipping_amount_0 = shipping_amount_0 + 0.5
    shipping_capped_0 = min(shipping_amount_0, 50)
    return {"rule": 0, "amount": shipping_capped_0, "subtotal": subtotal}


def shipping_rule_1(subtotal: float, region: str) -> Dict[str, float]:
    """Shipping rule 1: 0.017 rate, 0.75 fee in south, capped at 55."""
    shipping_amount_1 = round(subtotal * 0.017, 2)
    if region == "south":
        shipping_amount_1 = shipping_amount_1 + 0.75
    shipping_capped_1 = min(shipping_amount_1, 55)
    return {"rule": 1, "amount": shipping_capped_1, "subtotal": subtotal}


def shipping_rule_2(subtotal: float, region: str) -> Dict[str, float]:
    """Shipping rule 2: 0.024 rate, 1.00 fee in east, capped at 60."""
    shipping_amount_2 = round(subtotal * 0.024, 2)
    if region == "east":
        shipping_amount_2 = shipping_amount_2 + 1.0
    shipping_capped_2 = min(shipping_amount_2, 60)
    return {"rule": 2, "amount": shipping_capped_2, "subtotal": subtotal}


def shipping_rule_3(subtotal: float, region: str) -> Dict[str, float]:
    """Shipping rule 3: 0.031 rate, 1.25 fee in west, capped at 65."""
    shipping_amount_3 = round(subtotal * 0.031, 2)
    if region == "west":
        shipping_amount_3 = shipping_amount_3 + 1.25
    shipping_capped_3 = min(shipping_amount_3, 65)
    return {"rule": 3, "amount": shipping_capped_3, "subtotal": subtotal}


def shipping_rule_4(subtotal: float, region: str) -> Dict[str, float]:
    """Shipping rule 4: 0.038 rate, 1.50 fee in central, capped at 70."""
    shipping_amount_4 = round(subtotal * 0.038, 2)
    if region == "central":
        shipping_amount_4 = shipping_amount_4 + 1.5
    shipping_capped_4 = min(shipping_amount_4, 70)
    return {"rule": 4, "amount": shipping_capped_4, "subtotal": subtotal}


def shipping_rule_5(subtotal: float, region: str) -> Dict[str, float]:
    """Shipping rule 5: 0.045 rate, 1.75 fee in coastal, capped at 75."""
    shipping_amount_5 = round(subtotal * 0.045, 2)
    if region == "coastal":
        shipping_amount_5 = shipping_amount_5 + 1.75
    shipping_capped_5 = min(shipping_amount_5, 75)
    return {"rule": 5, "amount": shipping_capped_5, "subtotal": subtotal}


def shipping_rule_6(subtotal: float, region: str) -> Dict[str, float]:
    """Shipping rule 6: 0.052 rate, 2.00 fee in alpine, capped at 80."""
    shipping_amount_6 = round(subtotal * 0.052, 2)
    if region == "alpine":
        shipping_amount_6 = shipping_amount_6 + 2.0
    shipping_capped_6 = min(shipping_amount_6, 80)
    return {"rule": 6, "amount": shipping_capped_6, "subtotal": subtotal}


def shipping_rule_7(subtotal: float, region: str) -> Dict[str, float]:
    """Shipping rule 7: 0.059 rate, 2.25 fee in metro, capped at 85."""
    shipping_amount_7 = round(subtotal * 0.059, 2)
    if region == "metro":
        shipping_amount_7 = shipping_amount_7 + 2.25
    shipping_capped_7 = min(shipping_amount_7, 85)
    return {"rule": 7, "amount": shipping_capped_7, "subtotal": subtotal}


SHIPPING_RULES = [
    shipping_rule_0,
    shipping_rule_1,
    shipping_rule_2,
    shipping_rule_3,
    shipping_rule_4,
    shipping_rule_5,
    shipping_rule_6,
    shipping_rule_7,
]
