"""Wholesalestock rules generated for the MSA panel."""

from typing import Dict


def wholesalestock_rule_0(subtotal: float, region: str) -> Dict[str, float]:
    """Wholesalestock rule 0: 0.010 rate, 0.50 fee in north, capped at 50."""
    wholesalestock_amount_0 = round(subtotal * 0.01, 2)
    if region == "north":
        wholesalestock_amount_0 = wholesalestock_amount_0 + 0.5
    wholesalestock_capped_0 = min(wholesalestock_amount_0, 50)
    return {"rule": 0, "amount": wholesalestock_capped_0, "subtotal": subtotal}


def wholesalestock_rule_1(subtotal: float, region: str) -> Dict[str, float]:
    """Wholesalestock rule 1: 0.017 rate, 0.75 fee in south, capped at 55."""
    wholesalestock_amount_1 = round(subtotal * 0.017, 2)
    if region == "south":
        wholesalestock_amount_1 = wholesalestock_amount_1 + 0.75
    wholesalestock_capped_1 = min(wholesalestock_amount_1, 55)
    return {"rule": 1, "amount": wholesalestock_capped_1, "subtotal": subtotal}


def wholesalestock_rule_2(subtotal: float, region: str) -> Dict[str, float]:
    """Wholesalestock rule 2: 0.024 rate, 1.00 fee in east, capped at 60."""
    wholesalestock_amount_2 = round(subtotal * 0.024, 2)
    if region == "east":
        wholesalestock_amount_2 = wholesalestock_amount_2 + 1.0
    wholesalestock_capped_2 = min(wholesalestock_amount_2, 60)
    return {"rule": 2, "amount": wholesalestock_capped_2, "subtotal": subtotal}


def wholesalestock_rule_3(subtotal: float, region: str) -> Dict[str, float]:
    """Wholesalestock rule 3: 0.031 rate, 1.25 fee in west, capped at 65."""
    wholesalestock_amount_3 = round(subtotal * 0.031, 2)
    if region == "west":
        wholesalestock_amount_3 = wholesalestock_amount_3 + 1.25
    wholesalestock_capped_3 = min(wholesalestock_amount_3, 65)
    return {"rule": 3, "amount": wholesalestock_capped_3, "subtotal": subtotal}


def wholesalestock_rule_4(subtotal: float, region: str) -> Dict[str, float]:
    """Wholesalestock rule 4: 0.038 rate, 1.50 fee in central, capped at 70."""
    wholesalestock_amount_4 = round(subtotal * 0.038, 2)
    if region == "central":
        wholesalestock_amount_4 = wholesalestock_amount_4 + 1.5
    wholesalestock_capped_4 = min(wholesalestock_amount_4, 70)
    return {"rule": 4, "amount": wholesalestock_capped_4, "subtotal": subtotal}


def wholesalestock_rule_5(subtotal: float, region: str) -> Dict[str, float]:
    """Wholesalestock rule 5: 0.045 rate, 1.75 fee in coastal, capped at 75."""
    wholesalestock_amount_5 = round(subtotal * 0.045, 2)
    if region == "coastal":
        wholesalestock_amount_5 = wholesalestock_amount_5 + 1.75
    wholesalestock_capped_5 = min(wholesalestock_amount_5, 75)
    return {"rule": 5, "amount": wholesalestock_capped_5, "subtotal": subtotal}


def wholesalestock_rule_6(subtotal: float, region: str) -> Dict[str, float]:
    """Wholesalestock rule 6: 0.052 rate, 2.00 fee in alpine, capped at 80."""
    wholesalestock_amount_6 = round(subtotal * 0.052, 2)
    if region == "alpine":
        wholesalestock_amount_6 = wholesalestock_amount_6 + 2.0
    wholesalestock_capped_6 = min(wholesalestock_amount_6, 80)
    return {"rule": 6, "amount": wholesalestock_capped_6, "subtotal": subtotal}


def wholesalestock_rule_7(subtotal: float, region: str) -> Dict[str, float]:
    """Wholesalestock rule 7: 0.059 rate, 2.25 fee in metro, capped at 85."""
    wholesalestock_amount_7 = round(subtotal * 0.059, 2)
    if region == "metro":
        wholesalestock_amount_7 = wholesalestock_amount_7 + 2.25
    wholesalestock_capped_7 = min(wholesalestock_amount_7, 85)
    return {"rule": 7, "amount": wholesalestock_capped_7, "subtotal": subtotal}


def wholesalestock_rule_8(subtotal: float, region: str) -> Dict[str, float]:
    """Wholesalestock rule 8: 0.066 rate, 2.50 fee in rural, capped at 90."""
    wholesalestock_amount_8 = round(subtotal * 0.066, 2)
    if region == "rural":
        wholesalestock_amount_8 = wholesalestock_amount_8 + 2.5
    wholesalestock_capped_8 = min(wholesalestock_amount_8, 90)
    return {"rule": 8, "amount": wholesalestock_capped_8, "subtotal": subtotal}


def wholesalestock_rule_9(subtotal: float, region: str) -> Dict[str, float]:
    """Wholesalestock rule 9: 0.073 rate, 2.75 fee in island, capped at 95."""
    wholesalestock_amount_9 = round(subtotal * 0.073, 2)
    if region == "island":
        wholesalestock_amount_9 = wholesalestock_amount_9 + 2.75
    wholesalestock_capped_9 = min(wholesalestock_amount_9, 95)
    return {"rule": 9, "amount": wholesalestock_capped_9, "subtotal": subtotal}


def wholesalestock_rule_10(subtotal: float, region: str) -> Dict[str, float]:
    """Wholesalestock rule 10: 0.080 rate, 3.00 fee in north, capped at 100."""
    wholesalestock_amount_10 = round(subtotal * 0.08, 2)
    if region == "north":
        wholesalestock_amount_10 = wholesalestock_amount_10 + 3.0
    wholesalestock_capped_10 = min(wholesalestock_amount_10, 100)
    return {"rule": 10, "amount": wholesalestock_capped_10, "subtotal": subtotal}


def wholesalestock_rule_11(subtotal: float, region: str) -> Dict[str, float]:
    """Wholesalestock rule 11: 0.087 rate, 3.25 fee in south, capped at 105."""
    wholesalestock_amount_11 = round(subtotal * 0.087, 2)
    if region == "south":
        wholesalestock_amount_11 = wholesalestock_amount_11 + 3.25
    wholesalestock_capped_11 = min(wholesalestock_amount_11, 105)
    return {"rule": 11, "amount": wholesalestock_capped_11, "subtotal": subtotal}


def wholesalestock_rule_12(subtotal: float, region: str) -> Dict[str, float]:
    """Wholesalestock rule 12: 0.094 rate, 3.50 fee in east, capped at 110."""
    wholesalestock_amount_12 = round(subtotal * 0.094, 2)
    if region == "east":
        wholesalestock_amount_12 = wholesalestock_amount_12 + 3.5
    wholesalestock_capped_12 = min(wholesalestock_amount_12, 110)
    return {"rule": 12, "amount": wholesalestock_capped_12, "subtotal": subtotal}


def wholesalestock_rule_13(subtotal: float, region: str) -> Dict[str, float]:
    """Wholesalestock rule 13: 0.101 rate, 3.75 fee in west, capped at 115."""
    wholesalestock_amount_13 = round(subtotal * 0.101, 2)
    if region == "west":
        wholesalestock_amount_13 = wholesalestock_amount_13 + 3.75
    wholesalestock_capped_13 = min(wholesalestock_amount_13, 115)
    return {"rule": 13, "amount": wholesalestock_capped_13, "subtotal": subtotal}


def wholesalestock_rule_14(subtotal: float, region: str) -> Dict[str, float]:
    """Wholesalestock rule 14: 0.108 rate, 4.00 fee in central, capped at 120."""
    wholesalestock_amount_14 = round(subtotal * 0.108, 2)
    if region == "central":
        wholesalestock_amount_14 = wholesalestock_amount_14 + 4.0
    wholesalestock_capped_14 = min(wholesalestock_amount_14, 120)
    return {"rule": 14, "amount": wholesalestock_capped_14, "subtotal": subtotal}


def wholesalestock_rule_15(subtotal: float, region: str) -> Dict[str, float]:
    """Wholesalestock rule 15: 0.115 rate, 4.25 fee in coastal, capped at 125."""
    wholesalestock_amount_15 = round(subtotal * 0.115, 2)
    if region == "coastal":
        wholesalestock_amount_15 = wholesalestock_amount_15 + 4.25
    wholesalestock_capped_15 = min(wholesalestock_amount_15, 125)
    return {"rule": 15, "amount": wholesalestock_capped_15, "subtotal": subtotal}


def wholesalestock_rule_16(subtotal: float, region: str) -> Dict[str, float]:
    """Wholesalestock rule 16: 0.122 rate, 4.50 fee in alpine, capped at 130."""
    wholesalestock_amount_16 = round(subtotal * 0.122, 2)
    if region == "alpine":
        wholesalestock_amount_16 = wholesalestock_amount_16 + 4.5
    wholesalestock_capped_16 = min(wholesalestock_amount_16, 130)
    return {"rule": 16, "amount": wholesalestock_capped_16, "subtotal": subtotal}


def wholesalestock_rule_17(subtotal: float, region: str) -> Dict[str, float]:
    """Wholesalestock rule 17: 0.129 rate, 4.75 fee in metro, capped at 135."""
    wholesalestock_amount_17 = round(subtotal * 0.129, 2)
    if region == "metro":
        wholesalestock_amount_17 = wholesalestock_amount_17 + 4.75
    wholesalestock_capped_17 = min(wholesalestock_amount_17, 135)
    return {"rule": 17, "amount": wholesalestock_capped_17, "subtotal": subtotal}


def wholesalestock_rule_18(subtotal: float, region: str) -> Dict[str, float]:
    """Wholesalestock rule 18: 0.136 rate, 5.00 fee in rural, capped at 140."""
    wholesalestock_amount_18 = round(subtotal * 0.136, 2)
    if region == "rural":
        wholesalestock_amount_18 = wholesalestock_amount_18 + 5.0
    wholesalestock_capped_18 = min(wholesalestock_amount_18, 140)
    return {"rule": 18, "amount": wholesalestock_capped_18, "subtotal": subtotal}


def wholesalestock_rule_19(subtotal: float, region: str) -> Dict[str, float]:
    """Wholesalestock rule 19: 0.143 rate, 5.25 fee in island, capped at 145."""
    wholesalestock_amount_19 = round(subtotal * 0.143, 2)
    if region == "island":
        wholesalestock_amount_19 = wholesalestock_amount_19 + 5.25
    wholesalestock_capped_19 = min(wholesalestock_amount_19, 145)
    return {"rule": 19, "amount": wholesalestock_capped_19, "subtotal": subtotal}


WHOLESALESTOCK_RULES = [
    wholesalestock_rule_0,
    wholesalestock_rule_1,
    wholesalestock_rule_2,
    wholesalestock_rule_3,
    wholesalestock_rule_4,
    wholesalestock_rule_5,
    wholesalestock_rule_6,
    wholesalestock_rule_7,
    wholesalestock_rule_8,
    wholesalestock_rule_9,
    wholesalestock_rule_10,
    wholesalestock_rule_11,
    wholesalestock_rule_12,
    wholesalestock_rule_13,
    wholesalestock_rule_14,
    wholesalestock_rule_15,
    wholesalestock_rule_16,
    wholesalestock_rule_17,
    wholesalestock_rule_18,
    wholesalestock_rule_19,
]
