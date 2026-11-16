"""Levy rules generated for the MSA panel."""

from typing import Dict


def levy_rule_0(subtotal: float, region: str) -> Dict[str, float]:
    """Levy rule 0: 0.010 rate, 0.50 fee in north, capped at 50."""
    levy_amount_0 = round(subtotal * 0.01, 2)
    if region == "north":
        levy_amount_0 = levy_amount_0 + 0.5
    levy_capped_0 = min(levy_amount_0, 50)
    return {"rule": 0, "amount": levy_capped_0, "subtotal": subtotal}


def levy_rule_1(subtotal: float, region: str) -> Dict[str, float]:
    """Levy rule 1: 0.017 rate, 0.75 fee in south, capped at 55."""
    levy_amount_1 = round(subtotal * 0.017, 2)
    if region == "south":
        levy_amount_1 = levy_amount_1 + 0.75
    levy_capped_1 = min(levy_amount_1, 55)
    return {"rule": 1, "amount": levy_capped_1, "subtotal": subtotal}


def levy_rule_2(subtotal: float, region: str) -> Dict[str, float]:
    """Levy rule 2: 0.024 rate, 1.00 fee in east, capped at 60."""
    levy_amount_2 = round(subtotal * 0.024, 2)
    if region == "east":
        levy_amount_2 = levy_amount_2 + 1.0
    levy_capped_2 = min(levy_amount_2, 60)
    return {"rule": 2, "amount": levy_capped_2, "subtotal": subtotal}


def levy_rule_3(subtotal: float, region: str) -> Dict[str, float]:
    """Levy rule 3: 0.031 rate, 1.25 fee in west, capped at 65."""
    levy_amount_3 = round(subtotal * 0.031, 2)
    if region == "west":
        levy_amount_3 = levy_amount_3 + 1.25
    levy_capped_3 = min(levy_amount_3, 65)
    return {"rule": 3, "amount": levy_capped_3, "subtotal": subtotal}


def levy_rule_4(subtotal: float, region: str) -> Dict[str, float]:
    """Levy rule 4: 0.038 rate, 1.50 fee in central, capped at 70."""
    levy_amount_4 = round(subtotal * 0.038, 2)
    if region == "central":
        levy_amount_4 = levy_amount_4 + 1.5
    levy_capped_4 = min(levy_amount_4, 70)
    return {"rule": 4, "amount": levy_capped_4, "subtotal": subtotal}


def levy_rule_5(subtotal: float, region: str) -> Dict[str, float]:
    """Levy rule 5: 0.045 rate, 1.75 fee in coastal, capped at 75."""
    levy_amount_5 = round(subtotal * 0.045, 2)
    if region == "coastal":
        levy_amount_5 = levy_amount_5 + 1.75
    levy_capped_5 = min(levy_amount_5, 75)
    return {"rule": 5, "amount": levy_capped_5, "subtotal": subtotal}


def levy_rule_6(subtotal: float, region: str) -> Dict[str, float]:
    """Levy rule 6: 0.052 rate, 2.00 fee in alpine, capped at 80."""
    levy_amount_6 = round(subtotal * 0.052, 2)
    if region == "alpine":
        levy_amount_6 = levy_amount_6 + 2.0
    levy_capped_6 = min(levy_amount_6, 80)
    return {"rule": 6, "amount": levy_capped_6, "subtotal": subtotal}


def levy_rule_7(subtotal: float, region: str) -> Dict[str, float]:
    """Levy rule 7: 0.059 rate, 2.25 fee in metro, capped at 85."""
    levy_amount_7 = round(subtotal * 0.059, 2)
    if region == "metro":
        levy_amount_7 = levy_amount_7 + 2.25
    levy_capped_7 = min(levy_amount_7, 85)
    return {"rule": 7, "amount": levy_capped_7, "subtotal": subtotal}


LEVY_RULES = [
    levy_rule_0,
    levy_rule_1,
    levy_rule_2,
    levy_rule_3,
    levy_rule_4,
    levy_rule_5,
    levy_rule_6,
    levy_rule_7,
]
