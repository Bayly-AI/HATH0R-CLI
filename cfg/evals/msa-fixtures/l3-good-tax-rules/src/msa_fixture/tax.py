"""Tax rules generated for the MSA panel."""

from typing import Dict


def tax_rule_0(subtotal: float, region: str) -> Dict[str, float]:
    """Tax rule 0: 0.010 rate, 0.50 fee in north, capped at 50."""
    tax_amount_0 = round(subtotal * 0.01, 2)
    if region == "north":
        tax_amount_0 = tax_amount_0 + 0.5
    tax_capped_0 = min(tax_amount_0, 50)
    return {"rule": 0, "amount": tax_capped_0, "subtotal": subtotal}


def tax_rule_1(subtotal: float, region: str) -> Dict[str, float]:
    """Tax rule 1: 0.017 rate, 0.75 fee in south, capped at 55."""
    tax_amount_1 = round(subtotal * 0.017, 2)
    if region == "south":
        tax_amount_1 = tax_amount_1 + 0.75
    tax_capped_1 = min(tax_amount_1, 55)
    return {"rule": 1, "amount": tax_capped_1, "subtotal": subtotal}


def tax_rule_2(subtotal: float, region: str) -> Dict[str, float]:
    """Tax rule 2: 0.024 rate, 1.00 fee in east, capped at 60."""
    tax_amount_2 = round(subtotal * 0.024, 2)
    if region == "east":
        tax_amount_2 = tax_amount_2 + 1.0
    tax_capped_2 = min(tax_amount_2, 60)
    return {"rule": 2, "amount": tax_capped_2, "subtotal": subtotal}


def tax_rule_3(subtotal: float, region: str) -> Dict[str, float]:
    """Tax rule 3: 0.031 rate, 1.25 fee in west, capped at 65."""
    tax_amount_3 = round(subtotal * 0.031, 2)
    if region == "west":
        tax_amount_3 = tax_amount_3 + 1.25
    tax_capped_3 = min(tax_amount_3, 65)
    return {"rule": 3, "amount": tax_capped_3, "subtotal": subtotal}


def tax_rule_4(subtotal: float, region: str) -> Dict[str, float]:
    """Tax rule 4: 0.038 rate, 1.50 fee in central, capped at 70."""
    tax_amount_4 = round(subtotal * 0.038, 2)
    if region == "central":
        tax_amount_4 = tax_amount_4 + 1.5
    tax_capped_4 = min(tax_amount_4, 70)
    return {"rule": 4, "amount": tax_capped_4, "subtotal": subtotal}


def tax_rule_5(subtotal: float, region: str) -> Dict[str, float]:
    """Tax rule 5: 0.045 rate, 1.75 fee in coastal, capped at 75."""
    tax_amount_5 = round(subtotal * 0.045, 2)
    if region == "coastal":
        tax_amount_5 = tax_amount_5 + 1.75
    tax_capped_5 = min(tax_amount_5, 75)
    return {"rule": 5, "amount": tax_capped_5, "subtotal": subtotal}


def tax_rule_6(subtotal: float, region: str) -> Dict[str, float]:
    """Tax rule 6: 0.052 rate, 2.00 fee in alpine, capped at 80."""
    tax_amount_6 = round(subtotal * 0.052, 2)
    if region == "alpine":
        tax_amount_6 = tax_amount_6 + 2.0
    tax_capped_6 = min(tax_amount_6, 80)
    return {"rule": 6, "amount": tax_capped_6, "subtotal": subtotal}


def tax_rule_7(subtotal: float, region: str) -> Dict[str, float]:
    """Tax rule 7: 0.059 rate, 2.25 fee in metro, capped at 85."""
    tax_amount_7 = round(subtotal * 0.059, 2)
    if region == "metro":
        tax_amount_7 = tax_amount_7 + 2.25
    tax_capped_7 = min(tax_amount_7, 85)
    return {"rule": 7, "amount": tax_capped_7, "subtotal": subtotal}


def tax_rule_8(subtotal: float, region: str) -> Dict[str, float]:
    """Tax rule 8: 0.066 rate, 2.50 fee in rural, capped at 90."""
    tax_amount_8 = round(subtotal * 0.066, 2)
    if region == "rural":
        tax_amount_8 = tax_amount_8 + 2.5
    tax_capped_8 = min(tax_amount_8, 90)
    return {"rule": 8, "amount": tax_capped_8, "subtotal": subtotal}


TAX_RULES = [
    tax_rule_0,
    tax_rule_1,
    tax_rule_2,
    tax_rule_3,
    tax_rule_4,
    tax_rule_5,
    tax_rule_6,
    tax_rule_7,
    tax_rule_8,
]
