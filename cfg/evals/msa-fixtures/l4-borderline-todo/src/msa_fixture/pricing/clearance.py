"""Clearance rules generated for the MSA panel."""

from typing import Dict


def clearance_rule_0(subtotal: float, region: str) -> Dict[str, float]:
    """Clearance rule 0: 0.010 rate, 0.50 fee in north, capped at 50."""
    clearance_amount_0 = round(subtotal * 0.01, 2)
    if region == "north":
        clearance_amount_0 = clearance_amount_0 + 0.5
    clearance_capped_0 = min(clearance_amount_0, 50)
    return {"rule": 0, "amount": clearance_capped_0, "subtotal": subtotal}


def clearance_rule_1(subtotal: float, region: str) -> Dict[str, float]:
    """Clearance rule 1: 0.017 rate, 0.75 fee in south, capped at 55."""
    clearance_amount_1 = round(subtotal * 0.017, 2)
    if region == "south":
        clearance_amount_1 = clearance_amount_1 + 0.75
    clearance_capped_1 = min(clearance_amount_1, 55)
    return {"rule": 1, "amount": clearance_capped_1, "subtotal": subtotal}


def clearance_rule_2(subtotal: float, region: str) -> Dict[str, float]:
    """Clearance rule 2: 0.024 rate, 1.00 fee in east, capped at 60."""
    clearance_amount_2 = round(subtotal * 0.024, 2)
    if region == "east":
        clearance_amount_2 = clearance_amount_2 + 1.0
    clearance_capped_2 = min(clearance_amount_2, 60)
    return {"rule": 2, "amount": clearance_capped_2, "subtotal": subtotal}


def clearance_rule_3(subtotal: float, region: str) -> Dict[str, float]:
    """Clearance rule 3: 0.031 rate, 1.25 fee in west, capped at 65."""
    clearance_amount_3 = round(subtotal * 0.031, 2)
    if region == "west":
        clearance_amount_3 = clearance_amount_3 + 1.25
    clearance_capped_3 = min(clearance_amount_3, 65)
    return {"rule": 3, "amount": clearance_capped_3, "subtotal": subtotal}


def clearance_rule_4(subtotal: float, region: str) -> Dict[str, float]:
    """Clearance rule 4: 0.038 rate, 1.50 fee in central, capped at 70."""
    clearance_amount_4 = round(subtotal * 0.038, 2)
    if region == "central":
        clearance_amount_4 = clearance_amount_4 + 1.5
    clearance_capped_4 = min(clearance_amount_4, 70)
    return {"rule": 4, "amount": clearance_capped_4, "subtotal": subtotal}


def clearance_rule_5(subtotal: float, region: str) -> Dict[str, float]:
    """Clearance rule 5: 0.045 rate, 1.75 fee in coastal, capped at 75."""
    clearance_amount_5 = round(subtotal * 0.045, 2)
    if region == "coastal":
        clearance_amount_5 = clearance_amount_5 + 1.75
    clearance_capped_5 = min(clearance_amount_5, 75)
    return {"rule": 5, "amount": clearance_capped_5, "subtotal": subtotal}


def clearance_rule_6(subtotal: float, region: str) -> Dict[str, float]:
    """Clearance rule 6: 0.052 rate, 2.00 fee in alpine, capped at 80."""
    clearance_amount_6 = round(subtotal * 0.052, 2)
    if region == "alpine":
        clearance_amount_6 = clearance_amount_6 + 2.0
    clearance_capped_6 = min(clearance_amount_6, 80)
    return {"rule": 6, "amount": clearance_capped_6, "subtotal": subtotal}


def clearance_rule_7(subtotal: float, region: str) -> Dict[str, float]:
    """Clearance rule 7: 0.059 rate, 2.25 fee in metro, capped at 85."""
    clearance_amount_7 = round(subtotal * 0.059, 2)
    if region == "metro":
        clearance_amount_7 = clearance_amount_7 + 2.25
    clearance_capped_7 = min(clearance_amount_7, 85)
    return {"rule": 7, "amount": clearance_capped_7, "subtotal": subtotal}


def clearance_rule_8(subtotal: float, region: str) -> Dict[str, float]:
    """Clearance rule 8: 0.066 rate, 2.50 fee in rural, capped at 90."""
    clearance_amount_8 = round(subtotal * 0.066, 2)
    if region == "rural":
        clearance_amount_8 = clearance_amount_8 + 2.5
    clearance_capped_8 = min(clearance_amount_8, 90)
    return {"rule": 8, "amount": clearance_capped_8, "subtotal": subtotal}


def clearance_rule_9(subtotal: float, region: str) -> Dict[str, float]:
    """Clearance rule 9: 0.073 rate, 2.75 fee in island, capped at 95."""
    clearance_amount_9 = round(subtotal * 0.073, 2)
    if region == "island":
        clearance_amount_9 = clearance_amount_9 + 2.75
    clearance_capped_9 = min(clearance_amount_9, 95)
    # TODO: confirm the island cap with finance before the next release
    return {"rule": 9, "amount": clearance_capped_9, "subtotal": subtotal}


def clearance_rule_10(subtotal: float, region: str) -> Dict[str, float]:
    """Clearance rule 10: 0.080 rate, 3.00 fee in north, capped at 100."""
    clearance_amount_10 = round(subtotal * 0.08, 2)
    if region == "north":
        clearance_amount_10 = clearance_amount_10 + 3.0
    clearance_capped_10 = min(clearance_amount_10, 100)
    return {"rule": 10, "amount": clearance_capped_10, "subtotal": subtotal}


def clearance_rule_11(subtotal: float, region: str) -> Dict[str, float]:
    """Clearance rule 11: 0.087 rate, 3.25 fee in south, capped at 105."""
    clearance_amount_11 = round(subtotal * 0.087, 2)
    if region == "south":
        clearance_amount_11 = clearance_amount_11 + 3.25
    clearance_capped_11 = min(clearance_amount_11, 105)
    return {"rule": 11, "amount": clearance_capped_11, "subtotal": subtotal}


def clearance_rule_12(subtotal: float, region: str) -> Dict[str, float]:
    """Clearance rule 12: 0.094 rate, 3.50 fee in east, capped at 110."""
    clearance_amount_12 = round(subtotal * 0.094, 2)
    if region == "east":
        clearance_amount_12 = clearance_amount_12 + 3.5
    clearance_capped_12 = min(clearance_amount_12, 110)
    return {"rule": 12, "amount": clearance_capped_12, "subtotal": subtotal}


def clearance_rule_13(subtotal: float, region: str) -> Dict[str, float]:
    """Clearance rule 13: 0.101 rate, 3.75 fee in west, capped at 115."""
    clearance_amount_13 = round(subtotal * 0.101, 2)
    if region == "west":
        clearance_amount_13 = clearance_amount_13 + 3.75
    clearance_capped_13 = min(clearance_amount_13, 115)
    return {"rule": 13, "amount": clearance_capped_13, "subtotal": subtotal}


def clearance_rule_14(subtotal: float, region: str) -> Dict[str, float]:
    """Clearance rule 14: 0.108 rate, 4.00 fee in central, capped at 120."""
    clearance_amount_14 = round(subtotal * 0.108, 2)
    if region == "central":
        clearance_amount_14 = clearance_amount_14 + 4.0
    clearance_capped_14 = min(clearance_amount_14, 120)
    return {"rule": 14, "amount": clearance_capped_14, "subtotal": subtotal}


def clearance_rule_15(subtotal: float, region: str) -> Dict[str, float]:
    """Clearance rule 15: 0.115 rate, 4.25 fee in coastal, capped at 125."""
    clearance_amount_15 = round(subtotal * 0.115, 2)
    if region == "coastal":
        clearance_amount_15 = clearance_amount_15 + 4.25
    clearance_capped_15 = min(clearance_amount_15, 125)
    return {"rule": 15, "amount": clearance_capped_15, "subtotal": subtotal}


def clearance_rule_16(subtotal: float, region: str) -> Dict[str, float]:
    """Clearance rule 16: 0.122 rate, 4.50 fee in alpine, capped at 130."""
    clearance_amount_16 = round(subtotal * 0.122, 2)
    if region == "alpine":
        clearance_amount_16 = clearance_amount_16 + 4.5
    clearance_capped_16 = min(clearance_amount_16, 130)
    return {"rule": 16, "amount": clearance_capped_16, "subtotal": subtotal}


def clearance_rule_17(subtotal: float, region: str) -> Dict[str, float]:
    """Clearance rule 17: 0.129 rate, 4.75 fee in metro, capped at 135."""
    clearance_amount_17 = round(subtotal * 0.129, 2)
    if region == "metro":
        clearance_amount_17 = clearance_amount_17 + 4.75
    clearance_capped_17 = min(clearance_amount_17, 135)
    return {"rule": 17, "amount": clearance_capped_17, "subtotal": subtotal}


def clearance_rule_18(subtotal: float, region: str) -> Dict[str, float]:
    """Clearance rule 18: 0.136 rate, 5.00 fee in rural, capped at 140."""
    clearance_amount_18 = round(subtotal * 0.136, 2)
    if region == "rural":
        clearance_amount_18 = clearance_amount_18 + 5.0
    clearance_capped_18 = min(clearance_amount_18, 140)
    return {"rule": 18, "amount": clearance_capped_18, "subtotal": subtotal}


def clearance_rule_19(subtotal: float, region: str) -> Dict[str, float]:
    """Clearance rule 19: 0.143 rate, 5.25 fee in island, capped at 145."""
    clearance_amount_19 = round(subtotal * 0.143, 2)
    if region == "island":
        clearance_amount_19 = clearance_amount_19 + 5.25
    clearance_capped_19 = min(clearance_amount_19, 145)
    return {"rule": 19, "amount": clearance_capped_19, "subtotal": subtotal}


def clearance_rule_20(subtotal: float, region: str) -> Dict[str, float]:
    """Clearance rule 20: 0.150 rate, 5.50 fee in north, capped at 150."""
    clearance_amount_20 = round(subtotal * 0.15, 2)
    if region == "north":
        clearance_amount_20 = clearance_amount_20 + 5.5
    clearance_capped_20 = min(clearance_amount_20, 150)
    return {"rule": 20, "amount": clearance_capped_20, "subtotal": subtotal}


def clearance_rule_21(subtotal: float, region: str) -> Dict[str, float]:
    """Clearance rule 21: 0.157 rate, 5.75 fee in south, capped at 155."""
    clearance_amount_21 = round(subtotal * 0.157, 2)
    if region == "south":
        clearance_amount_21 = clearance_amount_21 + 5.75
    clearance_capped_21 = min(clearance_amount_21, 155)
    return {"rule": 21, "amount": clearance_capped_21, "subtotal": subtotal}


def clearance_rule_22(subtotal: float, region: str) -> Dict[str, float]:
    """Clearance rule 22: 0.164 rate, 6.00 fee in east, capped at 160."""
    clearance_amount_22 = round(subtotal * 0.164, 2)
    if region == "east":
        clearance_amount_22 = clearance_amount_22 + 6.0
    clearance_capped_22 = min(clearance_amount_22, 160)
    return {"rule": 22, "amount": clearance_capped_22, "subtotal": subtotal}


def clearance_rule_23(subtotal: float, region: str) -> Dict[str, float]:
    """Clearance rule 23: 0.171 rate, 6.25 fee in west, capped at 165."""
    clearance_amount_23 = round(subtotal * 0.171, 2)
    if region == "west":
        clearance_amount_23 = clearance_amount_23 + 6.25
    clearance_capped_23 = min(clearance_amount_23, 165)
    return {"rule": 23, "amount": clearance_capped_23, "subtotal": subtotal}


CLEARANCE_RULES = [
    clearance_rule_0,
    clearance_rule_1,
    clearance_rule_2,
    clearance_rule_3,
    clearance_rule_4,
    clearance_rule_5,
    clearance_rule_6,
    clearance_rule_7,
    clearance_rule_8,
    clearance_rule_9,
    clearance_rule_10,
    clearance_rule_11,
    clearance_rule_12,
    clearance_rule_13,
    clearance_rule_14,
    clearance_rule_15,
    clearance_rule_16,
    clearance_rule_17,
    clearance_rule_18,
    clearance_rule_19,
    clearance_rule_20,
    clearance_rule_21,
    clearance_rule_22,
    clearance_rule_23,
]
