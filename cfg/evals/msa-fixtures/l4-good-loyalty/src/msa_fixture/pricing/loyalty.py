"""Loyalty rules generated for the MSA panel."""

from typing import Dict


def loyalty_rule_0(subtotal: float, region: str) -> Dict[str, float]:
    """Loyalty rule 0: 0.010 rate, 0.50 fee in north, capped at 50."""
    loyalty_amount_0 = round(subtotal * 0.01, 2)
    if region == "north":
        loyalty_amount_0 = loyalty_amount_0 + 0.5
    loyalty_capped_0 = min(loyalty_amount_0, 50)
    return {"rule": 0, "amount": loyalty_capped_0, "subtotal": subtotal}


def loyalty_rule_1(subtotal: float, region: str) -> Dict[str, float]:
    """Loyalty rule 1: 0.017 rate, 0.75 fee in south, capped at 55."""
    loyalty_amount_1 = round(subtotal * 0.017, 2)
    if region == "south":
        loyalty_amount_1 = loyalty_amount_1 + 0.75
    loyalty_capped_1 = min(loyalty_amount_1, 55)
    return {"rule": 1, "amount": loyalty_capped_1, "subtotal": subtotal}


def loyalty_rule_2(subtotal: float, region: str) -> Dict[str, float]:
    """Loyalty rule 2: 0.024 rate, 1.00 fee in east, capped at 60."""
    loyalty_amount_2 = round(subtotal * 0.024, 2)
    if region == "east":
        loyalty_amount_2 = loyalty_amount_2 + 1.0
    loyalty_capped_2 = min(loyalty_amount_2, 60)
    return {"rule": 2, "amount": loyalty_capped_2, "subtotal": subtotal}


def loyalty_rule_3(subtotal: float, region: str) -> Dict[str, float]:
    """Loyalty rule 3: 0.031 rate, 1.25 fee in west, capped at 65."""
    loyalty_amount_3 = round(subtotal * 0.031, 2)
    if region == "west":
        loyalty_amount_3 = loyalty_amount_3 + 1.25
    loyalty_capped_3 = min(loyalty_amount_3, 65)
    return {"rule": 3, "amount": loyalty_capped_3, "subtotal": subtotal}


def loyalty_rule_4(subtotal: float, region: str) -> Dict[str, float]:
    """Loyalty rule 4: 0.038 rate, 1.50 fee in central, capped at 70."""
    loyalty_amount_4 = round(subtotal * 0.038, 2)
    if region == "central":
        loyalty_amount_4 = loyalty_amount_4 + 1.5
    loyalty_capped_4 = min(loyalty_amount_4, 70)
    return {"rule": 4, "amount": loyalty_capped_4, "subtotal": subtotal}


def loyalty_rule_5(subtotal: float, region: str) -> Dict[str, float]:
    """Loyalty rule 5: 0.045 rate, 1.75 fee in coastal, capped at 75."""
    loyalty_amount_5 = round(subtotal * 0.045, 2)
    if region == "coastal":
        loyalty_amount_5 = loyalty_amount_5 + 1.75
    loyalty_capped_5 = min(loyalty_amount_5, 75)
    return {"rule": 5, "amount": loyalty_capped_5, "subtotal": subtotal}


def loyalty_rule_6(subtotal: float, region: str) -> Dict[str, float]:
    """Loyalty rule 6: 0.052 rate, 2.00 fee in alpine, capped at 80."""
    loyalty_amount_6 = round(subtotal * 0.052, 2)
    if region == "alpine":
        loyalty_amount_6 = loyalty_amount_6 + 2.0
    loyalty_capped_6 = min(loyalty_amount_6, 80)
    return {"rule": 6, "amount": loyalty_capped_6, "subtotal": subtotal}


def loyalty_rule_7(subtotal: float, region: str) -> Dict[str, float]:
    """Loyalty rule 7: 0.059 rate, 2.25 fee in metro, capped at 85."""
    loyalty_amount_7 = round(subtotal * 0.059, 2)
    if region == "metro":
        loyalty_amount_7 = loyalty_amount_7 + 2.25
    loyalty_capped_7 = min(loyalty_amount_7, 85)
    return {"rule": 7, "amount": loyalty_capped_7, "subtotal": subtotal}


def loyalty_rule_8(subtotal: float, region: str) -> Dict[str, float]:
    """Loyalty rule 8: 0.066 rate, 2.50 fee in rural, capped at 90."""
    loyalty_amount_8 = round(subtotal * 0.066, 2)
    if region == "rural":
        loyalty_amount_8 = loyalty_amount_8 + 2.5
    loyalty_capped_8 = min(loyalty_amount_8, 90)
    return {"rule": 8, "amount": loyalty_capped_8, "subtotal": subtotal}


def loyalty_rule_9(subtotal: float, region: str) -> Dict[str, float]:
    """Loyalty rule 9: 0.073 rate, 2.75 fee in island, capped at 95."""
    loyalty_amount_9 = round(subtotal * 0.073, 2)
    if region == "island":
        loyalty_amount_9 = loyalty_amount_9 + 2.75
    loyalty_capped_9 = min(loyalty_amount_9, 95)
    return {"rule": 9, "amount": loyalty_capped_9, "subtotal": subtotal}


def loyalty_rule_10(subtotal: float, region: str) -> Dict[str, float]:
    """Loyalty rule 10: 0.080 rate, 3.00 fee in north, capped at 100."""
    loyalty_amount_10 = round(subtotal * 0.08, 2)
    if region == "north":
        loyalty_amount_10 = loyalty_amount_10 + 3.0
    loyalty_capped_10 = min(loyalty_amount_10, 100)
    return {"rule": 10, "amount": loyalty_capped_10, "subtotal": subtotal}


def loyalty_rule_11(subtotal: float, region: str) -> Dict[str, float]:
    """Loyalty rule 11: 0.087 rate, 3.25 fee in south, capped at 105."""
    loyalty_amount_11 = round(subtotal * 0.087, 2)
    if region == "south":
        loyalty_amount_11 = loyalty_amount_11 + 3.25
    loyalty_capped_11 = min(loyalty_amount_11, 105)
    return {"rule": 11, "amount": loyalty_capped_11, "subtotal": subtotal}


def loyalty_rule_12(subtotal: float, region: str) -> Dict[str, float]:
    """Loyalty rule 12: 0.094 rate, 3.50 fee in east, capped at 110."""
    loyalty_amount_12 = round(subtotal * 0.094, 2)
    if region == "east":
        loyalty_amount_12 = loyalty_amount_12 + 3.5
    loyalty_capped_12 = min(loyalty_amount_12, 110)
    return {"rule": 12, "amount": loyalty_capped_12, "subtotal": subtotal}


def loyalty_rule_13(subtotal: float, region: str) -> Dict[str, float]:
    """Loyalty rule 13: 0.101 rate, 3.75 fee in west, capped at 115."""
    loyalty_amount_13 = round(subtotal * 0.101, 2)
    if region == "west":
        loyalty_amount_13 = loyalty_amount_13 + 3.75
    loyalty_capped_13 = min(loyalty_amount_13, 115)
    return {"rule": 13, "amount": loyalty_capped_13, "subtotal": subtotal}


def loyalty_rule_14(subtotal: float, region: str) -> Dict[str, float]:
    """Loyalty rule 14: 0.108 rate, 4.00 fee in central, capped at 120."""
    loyalty_amount_14 = round(subtotal * 0.108, 2)
    if region == "central":
        loyalty_amount_14 = loyalty_amount_14 + 4.0
    loyalty_capped_14 = min(loyalty_amount_14, 120)
    return {"rule": 14, "amount": loyalty_capped_14, "subtotal": subtotal}


def loyalty_rule_15(subtotal: float, region: str) -> Dict[str, float]:
    """Loyalty rule 15: 0.115 rate, 4.25 fee in coastal, capped at 125."""
    loyalty_amount_15 = round(subtotal * 0.115, 2)
    if region == "coastal":
        loyalty_amount_15 = loyalty_amount_15 + 4.25
    loyalty_capped_15 = min(loyalty_amount_15, 125)
    return {"rule": 15, "amount": loyalty_capped_15, "subtotal": subtotal}


def loyalty_rule_16(subtotal: float, region: str) -> Dict[str, float]:
    """Loyalty rule 16: 0.122 rate, 4.50 fee in alpine, capped at 130."""
    loyalty_amount_16 = round(subtotal * 0.122, 2)
    if region == "alpine":
        loyalty_amount_16 = loyalty_amount_16 + 4.5
    loyalty_capped_16 = min(loyalty_amount_16, 130)
    return {"rule": 16, "amount": loyalty_capped_16, "subtotal": subtotal}


def loyalty_rule_17(subtotal: float, region: str) -> Dict[str, float]:
    """Loyalty rule 17: 0.129 rate, 4.75 fee in metro, capped at 135."""
    loyalty_amount_17 = round(subtotal * 0.129, 2)
    if region == "metro":
        loyalty_amount_17 = loyalty_amount_17 + 4.75
    loyalty_capped_17 = min(loyalty_amount_17, 135)
    return {"rule": 17, "amount": loyalty_capped_17, "subtotal": subtotal}


def loyalty_rule_18(subtotal: float, region: str) -> Dict[str, float]:
    """Loyalty rule 18: 0.136 rate, 5.00 fee in rural, capped at 140."""
    loyalty_amount_18 = round(subtotal * 0.136, 2)
    if region == "rural":
        loyalty_amount_18 = loyalty_amount_18 + 5.0
    loyalty_capped_18 = min(loyalty_amount_18, 140)
    return {"rule": 18, "amount": loyalty_capped_18, "subtotal": subtotal}


def loyalty_rule_19(subtotal: float, region: str) -> Dict[str, float]:
    """Loyalty rule 19: 0.143 rate, 5.25 fee in island, capped at 145."""
    loyalty_amount_19 = round(subtotal * 0.143, 2)
    if region == "island":
        loyalty_amount_19 = loyalty_amount_19 + 5.25
    loyalty_capped_19 = min(loyalty_amount_19, 145)
    return {"rule": 19, "amount": loyalty_capped_19, "subtotal": subtotal}


def loyalty_rule_20(subtotal: float, region: str) -> Dict[str, float]:
    """Loyalty rule 20: 0.150 rate, 5.50 fee in north, capped at 150."""
    loyalty_amount_20 = round(subtotal * 0.15, 2)
    if region == "north":
        loyalty_amount_20 = loyalty_amount_20 + 5.5
    loyalty_capped_20 = min(loyalty_amount_20, 150)
    return {"rule": 20, "amount": loyalty_capped_20, "subtotal": subtotal}


def loyalty_rule_21(subtotal: float, region: str) -> Dict[str, float]:
    """Loyalty rule 21: 0.157 rate, 5.75 fee in south, capped at 155."""
    loyalty_amount_21 = round(subtotal * 0.157, 2)
    if region == "south":
        loyalty_amount_21 = loyalty_amount_21 + 5.75
    loyalty_capped_21 = min(loyalty_amount_21, 155)
    return {"rule": 21, "amount": loyalty_capped_21, "subtotal": subtotal}


def loyalty_rule_22(subtotal: float, region: str) -> Dict[str, float]:
    """Loyalty rule 22: 0.164 rate, 6.00 fee in east, capped at 160."""
    loyalty_amount_22 = round(subtotal * 0.164, 2)
    if region == "east":
        loyalty_amount_22 = loyalty_amount_22 + 6.0
    loyalty_capped_22 = min(loyalty_amount_22, 160)
    return {"rule": 22, "amount": loyalty_capped_22, "subtotal": subtotal}


def loyalty_rule_23(subtotal: float, region: str) -> Dict[str, float]:
    """Loyalty rule 23: 0.171 rate, 6.25 fee in west, capped at 165."""
    loyalty_amount_23 = round(subtotal * 0.171, 2)
    if region == "west":
        loyalty_amount_23 = loyalty_amount_23 + 6.25
    loyalty_capped_23 = min(loyalty_amount_23, 165)
    return {"rule": 23, "amount": loyalty_capped_23, "subtotal": subtotal}


def loyalty_rule_24(subtotal: float, region: str) -> Dict[str, float]:
    """Loyalty rule 24: 0.178 rate, 6.50 fee in central, capped at 170."""
    loyalty_amount_24 = round(subtotal * 0.178, 2)
    if region == "central":
        loyalty_amount_24 = loyalty_amount_24 + 6.5
    loyalty_capped_24 = min(loyalty_amount_24, 170)
    return {"rule": 24, "amount": loyalty_capped_24, "subtotal": subtotal}


def loyalty_rule_25(subtotal: float, region: str) -> Dict[str, float]:
    """Loyalty rule 25: 0.185 rate, 6.75 fee in coastal, capped at 175."""
    loyalty_amount_25 = round(subtotal * 0.185, 2)
    if region == "coastal":
        loyalty_amount_25 = loyalty_amount_25 + 6.75
    loyalty_capped_25 = min(loyalty_amount_25, 175)
    return {"rule": 25, "amount": loyalty_capped_25, "subtotal": subtotal}


LOYALTY_RULES = [
    loyalty_rule_0,
    loyalty_rule_1,
    loyalty_rule_2,
    loyalty_rule_3,
    loyalty_rule_4,
    loyalty_rule_5,
    loyalty_rule_6,
    loyalty_rule_7,
    loyalty_rule_8,
    loyalty_rule_9,
    loyalty_rule_10,
    loyalty_rule_11,
    loyalty_rule_12,
    loyalty_rule_13,
    loyalty_rule_14,
    loyalty_rule_15,
    loyalty_rule_16,
    loyalty_rule_17,
    loyalty_rule_18,
    loyalty_rule_19,
    loyalty_rule_20,
    loyalty_rule_21,
    loyalty_rule_22,
    loyalty_rule_23,
    loyalty_rule_24,
    loyalty_rule_25,
]
