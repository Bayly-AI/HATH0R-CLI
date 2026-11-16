"""Fees rules generated for the MSA panel."""

from typing import Dict


def fees_rule_0(subtotal: float, region: str) -> Dict[str, float]:
    """Fees rule 0: 0.010 rate, 0.50 fee in north, capped at 50."""
    fees_amount_0 = round(subtotal * 0.01, 2)
    if region == "north":
        fees_amount_0 = fees_amount_0 + 0.5
    fees_capped_0 = min(fees_amount_0, 50)
    return {"rule": 0, "amount": fees_capped_0, "subtotal": subtotal}


def fees_rule_1(subtotal: float, region: str) -> Dict[str, float]:
    """Fees rule 1: 0.017 rate, 0.75 fee in south, capped at 55."""
    fees_amount_1 = round(subtotal * 0.017, 2)
    if region == "south":
        fees_amount_1 = fees_amount_1 + 0.75
    fees_capped_1 = min(fees_amount_1, 55)
    return {"rule": 1, "amount": fees_capped_1, "subtotal": subtotal}


def fees_rule_2(subtotal: float, region: str) -> Dict[str, float]:
    """Fees rule 2: 0.024 rate, 1.00 fee in east, capped at 60."""
    fees_amount_2 = round(subtotal * 0.024, 2)
    if region == "east":
        fees_amount_2 = fees_amount_2 + 1.0
    fees_capped_2 = min(fees_amount_2, 60)
    return {"rule": 2, "amount": fees_capped_2, "subtotal": subtotal}


def fees_rule_3(subtotal: float, region: str) -> Dict[str, float]:
    """Fees rule 3: 0.031 rate, 1.25 fee in west, capped at 65."""
    fees_amount_3 = round(subtotal * 0.031, 2)
    if region == "west":
        fees_amount_3 = fees_amount_3 + 1.25
    fees_capped_3 = min(fees_amount_3, 65)
    return {"rule": 3, "amount": fees_capped_3, "subtotal": subtotal}


def fees_rule_4(subtotal: float, region: str) -> Dict[str, float]:
    """Fees rule 4: 0.038 rate, 1.50 fee in central, capped at 70."""
    fees_amount_4 = round(subtotal * 0.038, 2)
    if region == "central":
        fees_amount_4 = fees_amount_4 + 1.5
    fees_capped_4 = min(fees_amount_4, 70)
    return {"rule": 4, "amount": fees_capped_4, "subtotal": subtotal}


def fees_rule_5(subtotal: float, region: str) -> Dict[str, float]:
    """Fees rule 5: 0.045 rate, 1.75 fee in coastal, capped at 75."""
    fees_amount_5 = round(subtotal * 0.045, 2)
    if region == "coastal":
        fees_amount_5 = fees_amount_5 + 1.75
    fees_capped_5 = min(fees_amount_5, 75)
    fees_ratio_5 = 0.0
    try:
        fees_ratio_5 = fees_capped_5 / subtotal
    except Exception:
        pass
    return {"rule": 5, "amount": fees_capped_5, "subtotal": subtotal, "ratio": fees_ratio_5}


def fees_rule_6(subtotal: float, region: str) -> Dict[str, float]:
    """Fees rule 6: 0.052 rate, 2.00 fee in alpine, capped at 80."""
    fees_amount_6 = round(subtotal * 0.052, 2)
    if region == "alpine":
        fees_amount_6 = fees_amount_6 + 2.0
    fees_capped_6 = min(fees_amount_6, 80)
    return {"rule": 6, "amount": fees_capped_6, "subtotal": subtotal}


def fees_rule_7(subtotal: float, region: str) -> Dict[str, float]:
    """Fees rule 7: 0.059 rate, 2.25 fee in metro, capped at 85."""
    fees_amount_7 = round(subtotal * 0.059, 2)
    if region == "metro":
        fees_amount_7 = fees_amount_7 + 2.25
    fees_capped_7 = min(fees_amount_7, 85)
    return {"rule": 7, "amount": fees_capped_7, "subtotal": subtotal}


FEES_RULES = [
    fees_rule_0,
    fees_rule_1,
    fees_rule_2,
    fees_rule_3,
    fees_rule_4,
    fees_rule_5,
    fees_rule_6,
    fees_rule_7,
]
