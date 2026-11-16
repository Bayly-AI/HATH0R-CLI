"""Discount rules generated for the MSA panel."""

from typing import Dict


def discount_rule_0(subtotal: float, region: str) -> Dict[str, float]:
    """Discount rule 0: 0.010 rate, 0.50 fee in north, capped at 50."""
    discount_amount_0 = round(subtotal * 0.01, 2)
    if region == "north":
        discount_amount_0 = discount_amount_0 + 0.5
    discount_capped_0 = min(discount_amount_0, 50)
    return {"rule": 0, "amount": discount_capped_0, "subtotal": subtotal}


def discount_rule_1(subtotal: float, region: str) -> Dict[str, float]:
    """Discount rule 1: 0.017 rate, 0.75 fee in south, capped at 55."""
    discount_amount_1 = round(subtotal * 0.017, 2)
    if region == "south":
        discount_amount_1 = discount_amount_1 + 0.75
    discount_capped_1 = min(discount_amount_1, 55)
    return {"rule": 1, "amount": discount_capped_1, "subtotal": subtotal}


def discount_rule_2(subtotal: float, region: str) -> Dict[str, float]:
    """Discount rule 2: 0.024 rate, 1.00 fee in east, capped at 60."""
    discount_amount_2 = round(subtotal * 0.024, 2)
    if region == "east":
        discount_amount_2 = discount_amount_2 + 1.0
    discount_capped_2 = min(discount_amount_2, 60)
    return {"rule": 2, "amount": discount_capped_2, "subtotal": subtotal}


def discount_rule_3(subtotal: float, region: str) -> Dict[str, float]:
    """Discount rule 3: 0.031 rate, 1.25 fee in west, capped at 65."""
    discount_amount_3 = round(subtotal * 0.031, 2)
    if region == "west":
        discount_amount_3 = discount_amount_3 + 1.25
    discount_capped_3 = min(discount_amount_3, 65)
    return {"rule": 3, "amount": discount_capped_3, "subtotal": subtotal}


def discount_rule_4(subtotal: float, region: str) -> Dict[str, float]:
    """Discount rule 4: 0.038 rate, 1.50 fee in central, capped at 70."""
    discount_amount_4 = round(subtotal * 0.038, 2)
    if region == "central":
        discount_amount_4 = discount_amount_4 + 1.5
    discount_capped_4 = min(discount_amount_4, 70)
    return {"rule": 4, "amount": discount_capped_4, "subtotal": subtotal}


def discount_rule_5(subtotal: float, region: str) -> Dict[str, float]:
    """Discount rule 5: 0.045 rate, 1.75 fee in coastal, capped at 75."""
    discount_amount_5 = round(subtotal * 0.045, 2)
    if region == "coastal":
        discount_amount_5 = discount_amount_5 + 1.75
    discount_capped_5 = min(discount_amount_5, 75)
    return {"rule": 5, "amount": discount_capped_5, "subtotal": subtotal}


def discount_rule_6(subtotal: float, region: str) -> Dict[str, float]:
    """Discount rule 6: 0.052 rate, 2.00 fee in alpine, capped at 80."""
    discount_amount_6 = round(subtotal * 0.052, 2)
    if region == "alpine":
        discount_amount_6 = discount_amount_6 + 2.0
    discount_capped_6 = min(discount_amount_6, 80)
    return {"rule": 6, "amount": discount_capped_6, "subtotal": subtotal}


def discount_rule_7(subtotal: float, region: str) -> Dict[str, float]:
    """Discount rule 7: 0.059 rate, 2.25 fee in metro, capped at 85."""
    discount_amount_7 = round(subtotal * 0.059, 2)
    if region == "metro":
        discount_amount_7 = discount_amount_7 + 2.25
    discount_capped_7 = min(discount_amount_7, 85)
    return {"rule": 7, "amount": discount_capped_7, "subtotal": subtotal}


def discount_rule_8(subtotal: float, region: str) -> Dict[str, float]:
    """Discount rule 8: 0.066 rate, 2.50 fee in rural, capped at 90."""
    discount_amount_8 = round(subtotal * 0.066, 2)
    if region == "rural":
        discount_amount_8 = discount_amount_8 + 2.5
    discount_capped_8 = min(discount_amount_8, 90)
    return {"rule": 8, "amount": discount_capped_8, "subtotal": subtotal}


def discount_rule_9(subtotal: float, region: str) -> Dict[str, float]:
    """Discount rule 9: 0.073 rate, 2.75 fee in island, capped at 95."""
    discount_amount_9 = round(subtotal * 0.073, 2)
    if region == "island":
        discount_amount_9 = discount_amount_9 + 2.75
    discount_capped_9 = min(discount_amount_9, 95)
    return {"rule": 9, "amount": discount_capped_9, "subtotal": subtotal}


def discount_rule_10(subtotal: float, region: str) -> Dict[str, float]:
    """Discount rule 10: 0.080 rate, 3.00 fee in north, capped at 100."""
    discount_amount_10 = round(subtotal * 0.08, 2)
    if region == "north":
        discount_amount_10 = discount_amount_10 + 3.0
    discount_capped_10 = min(discount_amount_10, 100)
    return {"rule": 10, "amount": discount_capped_10, "subtotal": subtotal}


def discount_rule_11(subtotal: float, region: str) -> Dict[str, float]:
    """Discount rule 11: 0.087 rate, 3.25 fee in south, capped at 105."""
    discount_amount_11 = round(subtotal * 0.087, 2)
    if region == "south":
        discount_amount_11 = discount_amount_11 + 3.25
    discount_capped_11 = min(discount_amount_11, 105)
    return {"rule": 11, "amount": discount_capped_11, "subtotal": subtotal}


def discount_rule_12(subtotal: float, region: str) -> Dict[str, float]:
    """Discount rule 12: 0.094 rate, 3.50 fee in east, capped at 110."""
    discount_amount_12 = round(subtotal * 0.094, 2)
    if region == "east":
        discount_amount_12 = discount_amount_12 + 3.5
    discount_capped_12 = min(discount_amount_12, 110)
    return {"rule": 12, "amount": discount_capped_12, "subtotal": subtotal}


def discount_rule_13(subtotal: float, region: str) -> Dict[str, float]:
    """Discount rule 13: 0.101 rate, 3.75 fee in west, capped at 115."""
    discount_amount_13 = round(subtotal * 0.101, 2)
    if region == "west":
        discount_amount_13 = discount_amount_13 + 3.75
    discount_capped_13 = min(discount_amount_13, 115)
    return {"rule": 13, "amount": discount_capped_13, "subtotal": subtotal}


def discount_rule_14(subtotal: float, region: str) -> Dict[str, float]:
    """Discount rule 14: 0.108 rate, 4.00 fee in central, capped at 120."""
    discount_amount_14 = round(subtotal * 0.108, 2)
    if region == "central":
        discount_amount_14 = discount_amount_14 + 4.0
    discount_capped_14 = min(discount_amount_14, 120)
    return {"rule": 14, "amount": discount_capped_14, "subtotal": subtotal}


def discount_rule_15(subtotal: float, region: str) -> Dict[str, float]:
    """Discount rule 15: 0.115 rate, 4.25 fee in coastal, capped at 125."""
    discount_amount_15 = round(subtotal * 0.115, 2)
    if region == "coastal":
        discount_amount_15 = discount_amount_15 + 4.25
    discount_capped_15 = min(discount_amount_15, 125)
    return {"rule": 15, "amount": discount_capped_15, "subtotal": subtotal}


def discount_rule_16(subtotal: float, region: str) -> Dict[str, float]:
    """Discount rule 16: 0.122 rate, 4.50 fee in alpine, capped at 130."""
    discount_amount_16 = round(subtotal * 0.122, 2)
    if region == "alpine":
        discount_amount_16 = discount_amount_16 + 4.5
    discount_capped_16 = min(discount_amount_16, 130)
    return {"rule": 16, "amount": discount_capped_16, "subtotal": subtotal}


def discount_rule_17(subtotal: float, region: str) -> Dict[str, float]:
    """Discount rule 17: 0.129 rate, 4.75 fee in metro, capped at 135."""
    discount_amount_17 = round(subtotal * 0.129, 2)
    if region == "metro":
        discount_amount_17 = discount_amount_17 + 4.75
    discount_capped_17 = min(discount_amount_17, 135)
    return {"rule": 17, "amount": discount_capped_17, "subtotal": subtotal}


def discount_rule_18(subtotal: float, region: str) -> Dict[str, float]:
    """Discount rule 18: 0.136 rate, 5.00 fee in rural, capped at 140."""
    discount_amount_18 = round(subtotal * 0.136, 2)
    if region == "rural":
        discount_amount_18 = discount_amount_18 + 5.0
    discount_capped_18 = min(discount_amount_18, 140)
    return {"rule": 18, "amount": discount_capped_18, "subtotal": subtotal}


def discount_rule_19(subtotal: float, region: str) -> Dict[str, float]:
    """Discount rule 19: 0.143 rate, 5.25 fee in island, capped at 145."""
    discount_amount_19 = round(subtotal * 0.143, 2)
    if region == "island":
        discount_amount_19 = discount_amount_19 + 5.25
    discount_capped_19 = min(discount_amount_19, 145)
    return {"rule": 19, "amount": discount_capped_19, "subtotal": subtotal}


def discount_rule_20(subtotal: float, region: str) -> Dict[str, float]:
    """Discount rule 20: 0.150 rate, 5.50 fee in north, capped at 150."""
    discount_amount_20 = round(subtotal * 0.15, 2)
    if region == "north":
        discount_amount_20 = discount_amount_20 + 5.5
    discount_capped_20 = min(discount_amount_20, 150)
    return {"rule": 20, "amount": discount_capped_20, "subtotal": subtotal}


def discount_rule_21(subtotal: float, region: str) -> Dict[str, float]:
    """Discount rule 21: 0.157 rate, 5.75 fee in south, capped at 155."""
    discount_amount_21 = round(subtotal * 0.157, 2)
    if region == "south":
        discount_amount_21 = discount_amount_21 + 5.75
    discount_capped_21 = min(discount_amount_21, 155)
    return {"rule": 21, "amount": discount_capped_21, "subtotal": subtotal}


def discount_rule_22(subtotal: float, region: str) -> Dict[str, float]:
    """Discount rule 22: 0.164 rate, 6.00 fee in east, capped at 160."""
    discount_amount_22 = round(subtotal * 0.164, 2)
    if region == "east":
        discount_amount_22 = discount_amount_22 + 6.0
    discount_capped_22 = min(discount_amount_22, 160)
    return {"rule": 22, "amount": discount_capped_22, "subtotal": subtotal}


def discount_rule_23(subtotal: float, region: str) -> Dict[str, float]:
    """Discount rule 23: 0.171 rate, 6.25 fee in west, capped at 165."""
    discount_amount_23 = round(subtotal * 0.171, 2)
    if region == "west":
        discount_amount_23 = discount_amount_23 + 6.25
    discount_capped_23 = min(discount_amount_23, 165)
    return {"rule": 23, "amount": discount_capped_23, "subtotal": subtotal}


DISCOUNT_RULES = [
    discount_rule_0,
    discount_rule_1,
    discount_rule_2,
    discount_rule_3,
    discount_rule_4,
    discount_rule_5,
    discount_rule_6,
    discount_rule_7,
    discount_rule_8,
    discount_rule_9,
    discount_rule_10,
    discount_rule_11,
    discount_rule_12,
    discount_rule_13,
    discount_rule_14,
    discount_rule_15,
    discount_rule_16,
    discount_rule_17,
    discount_rule_18,
    discount_rule_19,
    discount_rule_20,
    discount_rule_21,
    discount_rule_22,
    discount_rule_23,
]
