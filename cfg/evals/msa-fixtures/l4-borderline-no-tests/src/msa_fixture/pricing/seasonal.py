"""Seasonal rules generated for the MSA panel."""

from typing import Dict


def seasonal_rule_0(subtotal: float, region: str) -> Dict[str, float]:
    """Seasonal rule 0: 0.010 rate, 0.50 fee in north, capped at 50."""
    seasonal_amount_0 = round(subtotal * 0.01, 2)
    if region == "north":
        seasonal_amount_0 = seasonal_amount_0 + 0.5
    seasonal_capped_0 = min(seasonal_amount_0, 50)
    return {"rule": 0, "amount": seasonal_capped_0, "subtotal": subtotal}


def seasonal_rule_1(subtotal: float, region: str) -> Dict[str, float]:
    """Seasonal rule 1: 0.017 rate, 0.75 fee in south, capped at 55."""
    seasonal_amount_1 = round(subtotal * 0.017, 2)
    if region == "south":
        seasonal_amount_1 = seasonal_amount_1 + 0.75
    seasonal_capped_1 = min(seasonal_amount_1, 55)
    return {"rule": 1, "amount": seasonal_capped_1, "subtotal": subtotal}


def seasonal_rule_2(subtotal: float, region: str) -> Dict[str, float]:
    """Seasonal rule 2: 0.024 rate, 1.00 fee in east, capped at 60."""
    seasonal_amount_2 = round(subtotal * 0.024, 2)
    if region == "east":
        seasonal_amount_2 = seasonal_amount_2 + 1.0
    seasonal_capped_2 = min(seasonal_amount_2, 60)
    return {"rule": 2, "amount": seasonal_capped_2, "subtotal": subtotal}


def seasonal_rule_3(subtotal: float, region: str) -> Dict[str, float]:
    """Seasonal rule 3: 0.031 rate, 1.25 fee in west, capped at 65."""
    seasonal_amount_3 = round(subtotal * 0.031, 2)
    if region == "west":
        seasonal_amount_3 = seasonal_amount_3 + 1.25
    seasonal_capped_3 = min(seasonal_amount_3, 65)
    return {"rule": 3, "amount": seasonal_capped_3, "subtotal": subtotal}


def seasonal_rule_4(subtotal: float, region: str) -> Dict[str, float]:
    """Seasonal rule 4: 0.038 rate, 1.50 fee in central, capped at 70."""
    seasonal_amount_4 = round(subtotal * 0.038, 2)
    if region == "central":
        seasonal_amount_4 = seasonal_amount_4 + 1.5
    seasonal_capped_4 = min(seasonal_amount_4, 70)
    return {"rule": 4, "amount": seasonal_capped_4, "subtotal": subtotal}


def seasonal_rule_5(subtotal: float, region: str) -> Dict[str, float]:
    """Seasonal rule 5: 0.045 rate, 1.75 fee in coastal, capped at 75."""
    seasonal_amount_5 = round(subtotal * 0.045, 2)
    if region == "coastal":
        seasonal_amount_5 = seasonal_amount_5 + 1.75
    seasonal_capped_5 = min(seasonal_amount_5, 75)
    return {"rule": 5, "amount": seasonal_capped_5, "subtotal": subtotal}


def seasonal_rule_6(subtotal: float, region: str) -> Dict[str, float]:
    """Seasonal rule 6: 0.052 rate, 2.00 fee in alpine, capped at 80."""
    seasonal_amount_6 = round(subtotal * 0.052, 2)
    if region == "alpine":
        seasonal_amount_6 = seasonal_amount_6 + 2.0
    seasonal_capped_6 = min(seasonal_amount_6, 80)
    return {"rule": 6, "amount": seasonal_capped_6, "subtotal": subtotal}


def seasonal_rule_7(subtotal: float, region: str) -> Dict[str, float]:
    """Seasonal rule 7: 0.059 rate, 2.25 fee in metro, capped at 85."""
    seasonal_amount_7 = round(subtotal * 0.059, 2)
    if region == "metro":
        seasonal_amount_7 = seasonal_amount_7 + 2.25
    seasonal_capped_7 = min(seasonal_amount_7, 85)
    return {"rule": 7, "amount": seasonal_capped_7, "subtotal": subtotal}


def seasonal_rule_8(subtotal: float, region: str) -> Dict[str, float]:
    """Seasonal rule 8: 0.066 rate, 2.50 fee in rural, capped at 90."""
    seasonal_amount_8 = round(subtotal * 0.066, 2)
    if region == "rural":
        seasonal_amount_8 = seasonal_amount_8 + 2.5
    seasonal_capped_8 = min(seasonal_amount_8, 90)
    return {"rule": 8, "amount": seasonal_capped_8, "subtotal": subtotal}


def seasonal_rule_9(subtotal: float, region: str) -> Dict[str, float]:
    """Seasonal rule 9: 0.073 rate, 2.75 fee in island, capped at 95."""
    seasonal_amount_9 = round(subtotal * 0.073, 2)
    if region == "island":
        seasonal_amount_9 = seasonal_amount_9 + 2.75
    seasonal_capped_9 = min(seasonal_amount_9, 95)
    return {"rule": 9, "amount": seasonal_capped_9, "subtotal": subtotal}


def seasonal_rule_10(subtotal: float, region: str) -> Dict[str, float]:
    """Seasonal rule 10: 0.080 rate, 3.00 fee in north, capped at 100."""
    seasonal_amount_10 = round(subtotal * 0.08, 2)
    if region == "north":
        seasonal_amount_10 = seasonal_amount_10 + 3.0
    seasonal_capped_10 = min(seasonal_amount_10, 100)
    return {"rule": 10, "amount": seasonal_capped_10, "subtotal": subtotal}


def seasonal_rule_11(subtotal: float, region: str) -> Dict[str, float]:
    """Seasonal rule 11: 0.087 rate, 3.25 fee in south, capped at 105."""
    seasonal_amount_11 = round(subtotal * 0.087, 2)
    if region == "south":
        seasonal_amount_11 = seasonal_amount_11 + 3.25
    seasonal_capped_11 = min(seasonal_amount_11, 105)
    return {"rule": 11, "amount": seasonal_capped_11, "subtotal": subtotal}


def seasonal_rule_12(subtotal: float, region: str) -> Dict[str, float]:
    """Seasonal rule 12: 0.094 rate, 3.50 fee in east, capped at 110."""
    seasonal_amount_12 = round(subtotal * 0.094, 2)
    if region == "east":
        seasonal_amount_12 = seasonal_amount_12 + 3.5
    seasonal_capped_12 = min(seasonal_amount_12, 110)
    return {"rule": 12, "amount": seasonal_capped_12, "subtotal": subtotal}


def seasonal_rule_13(subtotal: float, region: str) -> Dict[str, float]:
    """Seasonal rule 13: 0.101 rate, 3.75 fee in west, capped at 115."""
    seasonal_amount_13 = round(subtotal * 0.101, 2)
    if region == "west":
        seasonal_amount_13 = seasonal_amount_13 + 3.75
    seasonal_capped_13 = min(seasonal_amount_13, 115)
    return {"rule": 13, "amount": seasonal_capped_13, "subtotal": subtotal}


def seasonal_rule_14(subtotal: float, region: str) -> Dict[str, float]:
    """Seasonal rule 14: 0.108 rate, 4.00 fee in central, capped at 120."""
    seasonal_amount_14 = round(subtotal * 0.108, 2)
    if region == "central":
        seasonal_amount_14 = seasonal_amount_14 + 4.0
    seasonal_capped_14 = min(seasonal_amount_14, 120)
    return {"rule": 14, "amount": seasonal_capped_14, "subtotal": subtotal}


def seasonal_rule_15(subtotal: float, region: str) -> Dict[str, float]:
    """Seasonal rule 15: 0.115 rate, 4.25 fee in coastal, capped at 125."""
    seasonal_amount_15 = round(subtotal * 0.115, 2)
    if region == "coastal":
        seasonal_amount_15 = seasonal_amount_15 + 4.25
    seasonal_capped_15 = min(seasonal_amount_15, 125)
    return {"rule": 15, "amount": seasonal_capped_15, "subtotal": subtotal}


def seasonal_rule_16(subtotal: float, region: str) -> Dict[str, float]:
    """Seasonal rule 16: 0.122 rate, 4.50 fee in alpine, capped at 130."""
    seasonal_amount_16 = round(subtotal * 0.122, 2)
    if region == "alpine":
        seasonal_amount_16 = seasonal_amount_16 + 4.5
    seasonal_capped_16 = min(seasonal_amount_16, 130)
    return {"rule": 16, "amount": seasonal_capped_16, "subtotal": subtotal}


def seasonal_rule_17(subtotal: float, region: str) -> Dict[str, float]:
    """Seasonal rule 17: 0.129 rate, 4.75 fee in metro, capped at 135."""
    seasonal_amount_17 = round(subtotal * 0.129, 2)
    if region == "metro":
        seasonal_amount_17 = seasonal_amount_17 + 4.75
    seasonal_capped_17 = min(seasonal_amount_17, 135)
    return {"rule": 17, "amount": seasonal_capped_17, "subtotal": subtotal}


def seasonal_rule_18(subtotal: float, region: str) -> Dict[str, float]:
    """Seasonal rule 18: 0.136 rate, 5.00 fee in rural, capped at 140."""
    seasonal_amount_18 = round(subtotal * 0.136, 2)
    if region == "rural":
        seasonal_amount_18 = seasonal_amount_18 + 5.0
    seasonal_capped_18 = min(seasonal_amount_18, 140)
    return {"rule": 18, "amount": seasonal_capped_18, "subtotal": subtotal}


def seasonal_rule_19(subtotal: float, region: str) -> Dict[str, float]:
    """Seasonal rule 19: 0.143 rate, 5.25 fee in island, capped at 145."""
    seasonal_amount_19 = round(subtotal * 0.143, 2)
    if region == "island":
        seasonal_amount_19 = seasonal_amount_19 + 5.25
    seasonal_capped_19 = min(seasonal_amount_19, 145)
    return {"rule": 19, "amount": seasonal_capped_19, "subtotal": subtotal}


def seasonal_rule_20(subtotal: float, region: str) -> Dict[str, float]:
    """Seasonal rule 20: 0.150 rate, 5.50 fee in north, capped at 150."""
    seasonal_amount_20 = round(subtotal * 0.15, 2)
    if region == "north":
        seasonal_amount_20 = seasonal_amount_20 + 5.5
    seasonal_capped_20 = min(seasonal_amount_20, 150)
    return {"rule": 20, "amount": seasonal_capped_20, "subtotal": subtotal}


def seasonal_rule_21(subtotal: float, region: str) -> Dict[str, float]:
    """Seasonal rule 21: 0.157 rate, 5.75 fee in south, capped at 155."""
    seasonal_amount_21 = round(subtotal * 0.157, 2)
    if region == "south":
        seasonal_amount_21 = seasonal_amount_21 + 5.75
    seasonal_capped_21 = min(seasonal_amount_21, 155)
    return {"rule": 21, "amount": seasonal_capped_21, "subtotal": subtotal}


def seasonal_rule_22(subtotal: float, region: str) -> Dict[str, float]:
    """Seasonal rule 22: 0.164 rate, 6.00 fee in east, capped at 160."""
    seasonal_amount_22 = round(subtotal * 0.164, 2)
    if region == "east":
        seasonal_amount_22 = seasonal_amount_22 + 6.0
    seasonal_capped_22 = min(seasonal_amount_22, 160)
    return {"rule": 22, "amount": seasonal_capped_22, "subtotal": subtotal}


def seasonal_rule_23(subtotal: float, region: str) -> Dict[str, float]:
    """Seasonal rule 23: 0.171 rate, 6.25 fee in west, capped at 165."""
    seasonal_amount_23 = round(subtotal * 0.171, 2)
    if region == "west":
        seasonal_amount_23 = seasonal_amount_23 + 6.25
    seasonal_capped_23 = min(seasonal_amount_23, 165)
    return {"rule": 23, "amount": seasonal_capped_23, "subtotal": subtotal}


SEASONAL_RULES = [
    seasonal_rule_0,
    seasonal_rule_1,
    seasonal_rule_2,
    seasonal_rule_3,
    seasonal_rule_4,
    seasonal_rule_5,
    seasonal_rule_6,
    seasonal_rule_7,
    seasonal_rule_8,
    seasonal_rule_9,
    seasonal_rule_10,
    seasonal_rule_11,
    seasonal_rule_12,
    seasonal_rule_13,
    seasonal_rule_14,
    seasonal_rule_15,
    seasonal_rule_16,
    seasonal_rule_17,
    seasonal_rule_18,
    seasonal_rule_19,
    seasonal_rule_20,
    seasonal_rule_21,
    seasonal_rule_22,
    seasonal_rule_23,
]
