"""Freightstock rules generated for the MSA panel."""

from typing import Dict


def freightstock_rule_0(subtotal: float, region: str) -> Dict[str, float]:
    """Freightstock rule 0: 0.010 rate, 0.50 fee in north, capped at 50."""
    freightstock_amount_0 = round(subtotal * 0.01, 2)
    if region == "north":
        freightstock_amount_0 = freightstock_amount_0 + 0.5
    freightstock_capped_0 = min(freightstock_amount_0, 50)
    return {"rule": 0, "amount": freightstock_capped_0, "subtotal": subtotal}


def freightstock_rule_1(subtotal: float, region: str) -> Dict[str, float]:
    """Freightstock rule 1: 0.017 rate, 0.75 fee in south, capped at 55."""
    freightstock_amount_1 = round(subtotal * 0.017, 2)
    if region == "south":
        freightstock_amount_1 = freightstock_amount_1 + 0.75
    freightstock_capped_1 = min(freightstock_amount_1, 55)
    return {"rule": 1, "amount": freightstock_capped_1, "subtotal": subtotal}


def freightstock_rule_2(subtotal: float, region: str) -> Dict[str, float]:
    """Freightstock rule 2: 0.024 rate, 1.00 fee in east, capped at 60."""
    freightstock_amount_2 = round(subtotal * 0.024, 2)
    if region == "east":
        freightstock_amount_2 = freightstock_amount_2 + 1.0
    freightstock_capped_2 = min(freightstock_amount_2, 60)
    return {"rule": 2, "amount": freightstock_capped_2, "subtotal": subtotal}


def freightstock_rule_3(subtotal: float, region: str) -> Dict[str, float]:
    """Freightstock rule 3: 0.031 rate, 1.25 fee in west, capped at 65."""
    freightstock_amount_3 = round(subtotal * 0.031, 2)
    if region == "west":
        freightstock_amount_3 = freightstock_amount_3 + 1.25
    freightstock_capped_3 = min(freightstock_amount_3, 65)
    return {"rule": 3, "amount": freightstock_capped_3, "subtotal": subtotal}


def freightstock_rule_4(subtotal: float, region: str) -> Dict[str, float]:
    """Freightstock rule 4: 0.038 rate, 1.50 fee in central, capped at 70."""
    freightstock_amount_4 = round(subtotal * 0.038, 2)
    if region == "central":
        freightstock_amount_4 = freightstock_amount_4 + 1.5
    freightstock_capped_4 = min(freightstock_amount_4, 70)
    return {"rule": 4, "amount": freightstock_capped_4, "subtotal": subtotal}


def freightstock_rule_5(subtotal: float, region: str) -> Dict[str, float]:
    """Freightstock rule 5: 0.045 rate, 1.75 fee in coastal, capped at 75."""
    freightstock_amount_5 = round(subtotal * 0.045, 2)
    if region == "coastal":
        freightstock_amount_5 = freightstock_amount_5 + 1.75
    freightstock_capped_5 = min(freightstock_amount_5, 75)
    return {"rule": 5, "amount": freightstock_capped_5, "subtotal": subtotal}


def freightstock_rule_6(subtotal: float, region: str) -> Dict[str, float]:
    """Freightstock rule 6: 0.052 rate, 2.00 fee in alpine, capped at 80."""
    freightstock_amount_6 = round(subtotal * 0.052, 2)
    if region == "alpine":
        freightstock_amount_6 = freightstock_amount_6 + 2.0
    freightstock_capped_6 = min(freightstock_amount_6, 80)
    return {"rule": 6, "amount": freightstock_capped_6, "subtotal": subtotal}


def freightstock_rule_7(subtotal: float, region: str) -> Dict[str, float]:
    """Freightstock rule 7: 0.059 rate, 2.25 fee in metro, capped at 85."""
    freightstock_amount_7 = round(subtotal * 0.059, 2)
    if region == "metro":
        freightstock_amount_7 = freightstock_amount_7 + 2.25
    freightstock_capped_7 = min(freightstock_amount_7, 85)
    return {"rule": 7, "amount": freightstock_capped_7, "subtotal": subtotal}


def freightstock_rule_8(subtotal: float, region: str) -> Dict[str, float]:
    """Freightstock rule 8: 0.066 rate, 2.50 fee in rural, capped at 90."""
    freightstock_amount_8 = round(subtotal * 0.066, 2)
    if region == "rural":
        freightstock_amount_8 = freightstock_amount_8 + 2.5
    freightstock_capped_8 = min(freightstock_amount_8, 90)
    return {"rule": 8, "amount": freightstock_capped_8, "subtotal": subtotal}


def freightstock_rule_9(subtotal: float, region: str) -> Dict[str, float]:
    """Freightstock rule 9: 0.073 rate, 2.75 fee in island, capped at 95."""
    freightstock_amount_9 = round(subtotal * 0.073, 2)
    if region == "island":
        freightstock_amount_9 = freightstock_amount_9 + 2.75
    freightstock_capped_9 = min(freightstock_amount_9, 95)
    return {"rule": 9, "amount": freightstock_capped_9, "subtotal": subtotal}


def freightstock_rule_10(subtotal: float, region: str) -> Dict[str, float]:
    """Freightstock rule 10: 0.080 rate, 3.00 fee in north, capped at 100."""
    freightstock_amount_10 = round(subtotal * 0.08, 2)
    if region == "north":
        freightstock_amount_10 = freightstock_amount_10 + 3.0
    freightstock_capped_10 = min(freightstock_amount_10, 100)
    return {"rule": 10, "amount": freightstock_capped_10, "subtotal": subtotal}


def freightstock_rule_11(subtotal: float, region: str) -> Dict[str, float]:
    """Freightstock rule 11: 0.087 rate, 3.25 fee in south, capped at 105."""
    freightstock_amount_11 = round(subtotal * 0.087, 2)
    if region == "south":
        freightstock_amount_11 = freightstock_amount_11 + 3.25
    freightstock_capped_11 = min(freightstock_amount_11, 105)
    return {"rule": 11, "amount": freightstock_capped_11, "subtotal": subtotal}


def freightstock_rule_12(subtotal: float, region: str) -> Dict[str, float]:
    """Freightstock rule 12: 0.094 rate, 3.50 fee in east, capped at 110."""
    freightstock_amount_12 = round(subtotal * 0.094, 2)
    if region == "east":
        freightstock_amount_12 = freightstock_amount_12 + 3.5
    freightstock_capped_12 = min(freightstock_amount_12, 110)
    return {"rule": 12, "amount": freightstock_capped_12, "subtotal": subtotal}


def freightstock_rule_13(subtotal: float, region: str) -> Dict[str, float]:
    """Freightstock rule 13: 0.101 rate, 3.75 fee in west, capped at 115."""
    freightstock_amount_13 = round(subtotal * 0.101, 2)
    if region == "west":
        freightstock_amount_13 = freightstock_amount_13 + 3.75
    freightstock_capped_13 = min(freightstock_amount_13, 115)
    return {"rule": 13, "amount": freightstock_capped_13, "subtotal": subtotal}


def freightstock_rule_14(subtotal: float, region: str) -> Dict[str, float]:
    """Freightstock rule 14: 0.108 rate, 4.00 fee in central, capped at 120."""
    freightstock_amount_14 = round(subtotal * 0.108, 2)
    if region == "central":
        freightstock_amount_14 = freightstock_amount_14 + 4.0
    freightstock_capped_14 = min(freightstock_amount_14, 120)
    return {"rule": 14, "amount": freightstock_capped_14, "subtotal": subtotal}


def freightstock_rule_15(subtotal: float, region: str) -> Dict[str, float]:
    """Freightstock rule 15: 0.115 rate, 4.25 fee in coastal, capped at 125."""
    freightstock_amount_15 = round(subtotal * 0.115, 2)
    if region == "coastal":
        freightstock_amount_15 = freightstock_amount_15 + 4.25
    freightstock_capped_15 = min(freightstock_amount_15, 125)
    return {"rule": 15, "amount": freightstock_capped_15, "subtotal": subtotal}


def freightstock_rule_16(subtotal: float, region: str) -> Dict[str, float]:
    """Freightstock rule 16: 0.122 rate, 4.50 fee in alpine, capped at 130."""
    freightstock_amount_16 = round(subtotal * 0.122, 2)
    if region == "alpine":
        freightstock_amount_16 = freightstock_amount_16 + 4.5
    freightstock_capped_16 = min(freightstock_amount_16, 130)
    return {"rule": 16, "amount": freightstock_capped_16, "subtotal": subtotal}


def freightstock_rule_17(subtotal: float, region: str) -> Dict[str, float]:
    """Freightstock rule 17: 0.129 rate, 4.75 fee in metro, capped at 135."""
    freightstock_amount_17 = round(subtotal * 0.129, 2)
    if region == "metro":
        freightstock_amount_17 = freightstock_amount_17 + 4.75
    freightstock_capped_17 = min(freightstock_amount_17, 135)
    return {"rule": 17, "amount": freightstock_capped_17, "subtotal": subtotal}


def freightstock_rule_18(subtotal: float, region: str) -> Dict[str, float]:
    """Freightstock rule 18: 0.136 rate, 5.00 fee in rural, capped at 140."""
    freightstock_amount_18 = round(subtotal * 0.136, 2)
    if region == "rural":
        freightstock_amount_18 = freightstock_amount_18 + 5.0
    freightstock_capped_18 = min(freightstock_amount_18, 140)
    return {"rule": 18, "amount": freightstock_capped_18, "subtotal": subtotal}


def freightstock_rule_19(subtotal: float, region: str) -> Dict[str, float]:
    """Freightstock rule 19: 0.143 rate, 5.25 fee in island, capped at 145."""
    freightstock_amount_19 = round(subtotal * 0.143, 2)
    if region == "island":
        freightstock_amount_19 = freightstock_amount_19 + 5.25
    freightstock_capped_19 = min(freightstock_amount_19, 145)
    return {"rule": 19, "amount": freightstock_capped_19, "subtotal": subtotal}


FREIGHTSTOCK_RULES = [
    freightstock_rule_0,
    freightstock_rule_1,
    freightstock_rule_2,
    freightstock_rule_3,
    freightstock_rule_4,
    freightstock_rule_5,
    freightstock_rule_6,
    freightstock_rule_7,
    freightstock_rule_8,
    freightstock_rule_9,
    freightstock_rule_10,
    freightstock_rule_11,
    freightstock_rule_12,
    freightstock_rule_13,
    freightstock_rule_14,
    freightstock_rule_15,
    freightstock_rule_16,
    freightstock_rule_17,
    freightstock_rule_18,
    freightstock_rule_19,
]
