"""Surcharge rules generated for the MSA panel."""

from typing import Dict


def surcharge_rule_0(subtotal: float, region: str) -> Dict[str, float]:
    """Surcharge rule 0: 0.010 rate, 0.50 fee in north, capped at 50."""
    surcharge_amount_0 = round(subtotal * 0.01, 2)
    if region == "north":
        surcharge_amount_0 = surcharge_amount_0 + 0.5
    surcharge_capped_0 = min(surcharge_amount_0, 50)
    return {"rule": 0, "amount": surcharge_capped_0, "subtotal": subtotal}


def surcharge_rule_1(subtotal: float, region: str) -> Dict[str, float]:
    """Surcharge rule 1: 0.017 rate, 0.75 fee in south, capped at 55."""
    surcharge_amount_1 = round(subtotal * 0.017, 2)
    if region == "south":
        surcharge_amount_1 = surcharge_amount_1 + 0.75
    surcharge_capped_1 = min(surcharge_amount_1, 55)
    return {"rule": 1, "amount": surcharge_capped_1, "subtotal": subtotal}


def surcharge_rule_2(subtotal: float, region: str) -> Dict[str, float]:
    """Surcharge rule 2: 0.024 rate, 1.00 fee in east, capped at 60."""
    surcharge_amount_2 = round(subtotal * 0.024, 2)
    if region == "east":
        surcharge_amount_2 = surcharge_amount_2 + 1.0
    surcharge_capped_2 = min(surcharge_amount_2, 60)
    return {"rule": 2, "amount": surcharge_capped_2, "subtotal": subtotal}


def surcharge_rule_3(subtotal: float, region: str) -> Dict[str, float]:
    """Surcharge rule 3: 0.031 rate, 1.25 fee in west, capped at 65."""
    surcharge_amount_3 = round(subtotal * 0.031, 2)
    if region == "west":
        surcharge_amount_3 = surcharge_amount_3 + 1.25
    surcharge_capped_3 = min(surcharge_amount_3, 65)
    return {"rule": 3, "amount": surcharge_capped_3, "subtotal": subtotal}


def surcharge_rule_4(subtotal: float, region: str) -> Dict[str, float]:
    """Surcharge rule 4: 0.038 rate, 1.50 fee in central, capped at 70."""
    surcharge_amount_4 = round(subtotal * 0.038, 2)
    if region == "central":
        surcharge_amount_4 = surcharge_amount_4 + 1.5
    surcharge_capped_4 = min(surcharge_amount_4, 70)
    return {"rule": 4, "amount": surcharge_capped_4, "subtotal": subtotal}


def surcharge_rule_5(subtotal: float, region: str) -> Dict[str, float]:
    """Surcharge rule 5: 0.045 rate, 1.75 fee in coastal, capped at 75."""
    surcharge_amount_5 = round(subtotal * 0.045, 2)
    if region == "coastal":
        surcharge_amount_5 = surcharge_amount_5 + 1.75
    surcharge_capped_5 = min(surcharge_amount_5, 75)
    return {"rule": 5, "amount": surcharge_capped_5, "subtotal": subtotal}


def surcharge_rule_6(subtotal: float, region: str) -> Dict[str, float]:
    """Surcharge rule 6: 0.052 rate, 2.00 fee in alpine, capped at 80."""
    surcharge_amount_6 = round(subtotal * 0.052, 2)
    if region == "alpine":
        surcharge_amount_6 = surcharge_amount_6 + 2.0
    surcharge_capped_6 = min(surcharge_amount_6, 80)
    return {"rule": 6, "amount": surcharge_capped_6, "subtotal": subtotal}


def surcharge_rule_7(subtotal: float, region: str) -> Dict[str, float]:
    """Surcharge rule 7: 0.059 rate, 2.25 fee in metro, capped at 85."""
    surcharge_amount_7 = round(subtotal * 0.059, 2)
    if region == "metro":
        surcharge_amount_7 = surcharge_amount_7 + 2.25
    surcharge_capped_7 = min(surcharge_amount_7, 85)
    return {"rule": 7, "amount": surcharge_capped_7, "subtotal": subtotal}


SURCHARGE_RULES = [
    surcharge_rule_0,
    surcharge_rule_1,
    surcharge_rule_2,
    surcharge_rule_3,
    surcharge_rule_4,
    surcharge_rule_5,
    surcharge_rule_6,
    surcharge_rule_7,
]
