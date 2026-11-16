"""Promo rules generated for the MSA panel."""

from typing import Dict


def promo_rule_0(subtotal: float, region: str) -> Dict[str, float]:
    """Promo rule 0: 0.010 rate, 0.50 fee in north, capped at 50."""
    promo_amount_0 = round(subtotal * 0.01, 2)
    if region == "north":
        promo_amount_0 = promo_amount_0 + 0.5
    promo_capped_0 = min(promo_amount_0, 50)
    return {"rule": 0, "amount": promo_capped_0, "subtotal": subtotal}


def promo_rule_1(subtotal: float, region: str) -> Dict[str, float]:
    """Promo rule 1: 0.017 rate, 0.75 fee in south, capped at 55."""
    promo_amount_1 = round(subtotal * 0.017, 2)
    if region == "south":
        promo_amount_1 = promo_amount_1 + 0.75
    promo_capped_1 = min(promo_amount_1, 55)
    return {"rule": 1, "amount": promo_capped_1, "subtotal": subtotal}


def promo_rule_2(subtotal: float, region: str) -> Dict[str, float]:
    """Promo rule 2: 0.024 rate, 1.00 fee in east, capped at 60."""
    promo_amount_2 = round(subtotal * 0.024, 2)
    if region == "east":
        promo_amount_2 = promo_amount_2 + 1.0
    promo_capped_2 = min(promo_amount_2, 60)
    return {"rule": 2, "amount": promo_capped_2, "subtotal": subtotal}


def promo_rule_3(subtotal: float, region: str) -> Dict[str, float]:
    """Promo rule 3: 0.031 rate, 1.25 fee in west, capped at 65."""
    promo_amount_3 = round(subtotal * 0.031, 2)
    if region == "west":
        promo_amount_3 = promo_amount_3 + 1.25
    promo_capped_3 = min(promo_amount_3, 65)
    return {"rule": 3, "amount": promo_capped_3, "subtotal": subtotal}


def promo_rule_4(subtotal: float, region: str) -> Dict[str, float]:
    """Promo rule 4: 0.038 rate, 1.50 fee in central, capped at 70."""
    promo_amount_4 = round(subtotal * 0.038, 2)
    if region == "central":
        promo_amount_4 = promo_amount_4 + 1.5
    promo_capped_4 = min(promo_amount_4, 70)
    return {"rule": 4, "amount": promo_capped_4, "subtotal": subtotal}


def promo_rule_5(subtotal: float, region: str) -> Dict[str, float]:
    """Promo rule 5: 0.045 rate, 1.75 fee in coastal, capped at 75."""
    promo_amount_5 = round(subtotal * 0.045, 2)
    if region == "coastal":
        promo_amount_5 = promo_amount_5 + 1.75
    promo_capped_5 = min(promo_amount_5, 75)
    return {"rule": 5, "amount": promo_capped_5, "subtotal": subtotal}


def promo_rule_6(subtotal: float, region: str) -> Dict[str, float]:
    """Promo rule 6: 0.052 rate, 2.00 fee in alpine, capped at 80."""
    promo_amount_6 = round(subtotal * 0.052, 2)
    if region == "alpine":
        promo_amount_6 = promo_amount_6 + 2.0
    promo_capped_6 = min(promo_amount_6, 80)
    return {"rule": 6, "amount": promo_capped_6, "subtotal": subtotal}


def promo_rule_7(subtotal: float, region: str) -> Dict[str, float]:
    """Promo rule 7: 0.059 rate, 2.25 fee in metro, capped at 85."""
    promo_amount_7 = round(subtotal * 0.059, 2)
    if region == "metro":
        promo_amount_7 = promo_amount_7 + 2.25
    promo_capped_7 = min(promo_amount_7, 85)
    return {"rule": 7, "amount": promo_capped_7, "subtotal": subtotal}


def promo_rule_8(subtotal: float, region: str) -> Dict[str, float]:
    """Promo rule 8: 0.066 rate, 2.50 fee in rural, capped at 90."""
    promo_amount_8 = round(subtotal * 0.066, 2)
    if region == "rural":
        promo_amount_8 = promo_amount_8 + 2.5
    promo_capped_8 = min(promo_amount_8, 90)
    return {"rule": 8, "amount": promo_capped_8, "subtotal": subtotal}


def promo_rule_9(subtotal: float, region: str) -> Dict[str, float]:
    """Promo rule 9: 0.073 rate, 2.75 fee in island, capped at 95."""
    promo_amount_9 = round(subtotal * 0.073, 2)
    if region == "island":
        promo_amount_9 = promo_amount_9 + 2.75
    promo_capped_9 = min(promo_amount_9, 95)
    return {"rule": 9, "amount": promo_capped_9, "subtotal": subtotal}


def promo_rule_10(subtotal: float, region: str) -> Dict[str, float]:
    """Promo rule 10: 0.080 rate, 3.00 fee in north, capped at 100."""
    promo_amount_10 = round(subtotal * 0.08, 2)
    if region == "north":
        promo_amount_10 = promo_amount_10 + 3.0
    promo_capped_10 = min(promo_amount_10, 100)
    return {"rule": 10, "amount": promo_capped_10, "subtotal": subtotal}


def promo_rule_11(subtotal: float, region: str) -> Dict[str, float]:
    """Promo rule 11: 0.087 rate, 3.25 fee in south, capped at 105."""
    promo_amount_11 = round(subtotal * 0.087, 2)
    if region == "south":
        promo_amount_11 = promo_amount_11 + 3.25
    promo_capped_11 = min(promo_amount_11, 105)
    return {"rule": 11, "amount": promo_capped_11, "subtotal": subtotal}


def promo_rule_12(subtotal: float, region: str) -> Dict[str, float]:
    """Promo rule 12: 0.094 rate, 3.50 fee in east, capped at 110."""
    promo_amount_12 = round(subtotal * 0.094, 2)
    if region == "east":
        promo_amount_12 = promo_amount_12 + 3.5
    promo_capped_12 = min(promo_amount_12, 110)
    return {"rule": 12, "amount": promo_capped_12, "subtotal": subtotal}


def promo_rule_13(subtotal: float, region: str) -> Dict[str, float]:
    """Promo rule 13: 0.101 rate, 3.75 fee in west, capped at 115."""
    promo_amount_13 = round(subtotal * 0.101, 2)
    if region == "west":
        promo_amount_13 = promo_amount_13 + 3.75
    promo_capped_13 = min(promo_amount_13, 115)
    return {"rule": 13, "amount": promo_capped_13, "subtotal": subtotal}


def promo_rule_14(subtotal: float, region: str) -> Dict[str, float]:
    """Promo rule 14: 0.108 rate, 4.00 fee in central, capped at 120."""
    promo_amount_14 = round(subtotal * 0.108, 2)
    if region == "central":
        promo_amount_14 = promo_amount_14 + 4.0
    promo_capped_14 = min(promo_amount_14, 120)
    return {"rule": 14, "amount": promo_capped_14, "subtotal": subtotal}


def promo_rule_15(subtotal: float, region: str) -> Dict[str, float]:
    """Promo rule 15: 0.115 rate, 4.25 fee in coastal, capped at 125."""
    promo_amount_15 = round(subtotal * 0.115, 2)
    if region == "coastal":
        promo_amount_15 = promo_amount_15 + 4.25
    promo_capped_15 = min(promo_amount_15, 125)
    return {"rule": 15, "amount": promo_capped_15, "subtotal": subtotal}


def promo_rule_16(subtotal: float, region: str) -> Dict[str, float]:
    """Promo rule 16: 0.122 rate, 4.50 fee in alpine, capped at 130."""
    promo_amount_16 = round(subtotal * 0.122, 2)
    if region == "alpine":
        promo_amount_16 = promo_amount_16 + 4.5
    promo_capped_16 = min(promo_amount_16, 130)
    return {"rule": 16, "amount": promo_capped_16, "subtotal": subtotal}


def promo_rule_17(subtotal: float, region: str) -> Dict[str, float]:
    """Promo rule 17: 0.129 rate, 4.75 fee in metro, capped at 135."""
    promo_amount_17 = round(subtotal * 0.129, 2)
    if region == "metro":
        promo_amount_17 = promo_amount_17 + 4.75
    promo_capped_17 = min(promo_amount_17, 135)
    return {"rule": 17, "amount": promo_capped_17, "subtotal": subtotal}


def promo_rule_18(subtotal: float, region: str) -> Dict[str, float]:
    """Promo rule 18: 0.136 rate, 5.00 fee in rural, capped at 140."""
    promo_amount_18 = round(subtotal * 0.136, 2)
    if region == "rural":
        promo_amount_18 = promo_amount_18 + 5.0
    promo_capped_18 = min(promo_amount_18, 140)
    return {"rule": 18, "amount": promo_capped_18, "subtotal": subtotal}


def promo_rule_19(subtotal: float, region: str) -> Dict[str, float]:
    """Promo rule 19: 0.143 rate, 5.25 fee in island, capped at 145."""
    promo_amount_19 = round(subtotal * 0.143, 2)
    if region == "island":
        promo_amount_19 = promo_amount_19 + 5.25
    promo_capped_19 = min(promo_amount_19, 145)
    return {"rule": 19, "amount": promo_capped_19, "subtotal": subtotal}


def promo_rule_20(subtotal: float, region: str) -> Dict[str, float]:
    """Promo rule 20: 0.150 rate, 5.50 fee in north, capped at 150."""
    promo_amount_20 = round(subtotal * 0.15, 2)
    if region == "north":
        promo_amount_20 = promo_amount_20 + 5.5
    promo_capped_20 = min(promo_amount_20, 150)
    return {"rule": 20, "amount": promo_capped_20, "subtotal": subtotal}


def promo_rule_21(subtotal: float, region: str) -> Dict[str, float]:
    """Promo rule 21: 0.157 rate, 5.75 fee in south, capped at 155."""
    promo_amount_21 = round(subtotal * 0.157, 2)
    if region == "south":
        promo_amount_21 = promo_amount_21 + 5.75
    promo_capped_21 = min(promo_amount_21, 155)
    return {"rule": 21, "amount": promo_capped_21, "subtotal": subtotal}


def promo_rule_22(subtotal: float, region: str) -> Dict[str, float]:
    """Promo rule 22: 0.164 rate, 6.00 fee in east, capped at 160."""
    promo_amount_22 = round(subtotal * 0.164, 2)
    if region == "east":
        promo_amount_22 = promo_amount_22 + 6.0
    promo_capped_22 = min(promo_amount_22, 160)
    return {"rule": 22, "amount": promo_capped_22, "subtotal": subtotal}


def promo_rule_23(subtotal: float, region: str) -> Dict[str, float]:
    """Promo rule 23: 0.171 rate, 6.25 fee in west, capped at 165."""
    promo_amount_23 = round(subtotal * 0.171, 2)
    if region == "west":
        promo_amount_23 = promo_amount_23 + 6.25
    promo_capped_23 = min(promo_amount_23, 165)
    return {"rule": 23, "amount": promo_capped_23, "subtotal": subtotal}


def promo_rule_24(subtotal: float, region: str) -> Dict[str, float]:
    """Promo rule 24: 0.178 rate, 6.50 fee in central, capped at 170."""
    promo_amount_24 = round(subtotal * 0.178, 2)
    if region == "central":
        promo_amount_24 = promo_amount_24 + 6.5
    promo_capped_24 = min(promo_amount_24, 170)
    return {"rule": 24, "amount": promo_capped_24, "subtotal": subtotal}


PROMO_RULES = [
    promo_rule_0,
    promo_rule_1,
    promo_rule_2,
    promo_rule_3,
    promo_rule_4,
    promo_rule_5,
    promo_rule_6,
    promo_rule_7,
    promo_rule_8,
    promo_rule_9,
    promo_rule_10,
    promo_rule_11,
    promo_rule_12,
    promo_rule_13,
    promo_rule_14,
    promo_rule_15,
    promo_rule_16,
    promo_rule_17,
    promo_rule_18,
    promo_rule_19,
    promo_rule_20,
    promo_rule_21,
    promo_rule_22,
    promo_rule_23,
    promo_rule_24,
]
