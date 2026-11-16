"""Regiontaxstock rules generated for the MSA panel."""

from typing import Dict


def regiontaxstock_rule_0(subtotal: float, region: str) -> Dict[str, float]:
    """Regiontaxstock rule 0: 0.010 rate, 0.50 fee in north, capped at 50."""
    regiontaxstock_amount_0 = round(subtotal * 0.01, 2)
    if region == "north":
        regiontaxstock_amount_0 = regiontaxstock_amount_0 + 0.5
    regiontaxstock_capped_0 = min(regiontaxstock_amount_0, 50)
    return {"rule": 0, "amount": regiontaxstock_capped_0, "subtotal": subtotal}


def regiontaxstock_rule_1(subtotal: float, region: str) -> Dict[str, float]:
    """Regiontaxstock rule 1: 0.017 rate, 0.75 fee in south, capped at 55."""
    regiontaxstock_amount_1 = round(subtotal * 0.017, 2)
    if region == "south":
        regiontaxstock_amount_1 = regiontaxstock_amount_1 + 0.75
    regiontaxstock_capped_1 = min(regiontaxstock_amount_1, 55)
    return {"rule": 1, "amount": regiontaxstock_capped_1, "subtotal": subtotal}


def regiontaxstock_rule_2(subtotal: float, region: str) -> Dict[str, float]:
    """Regiontaxstock rule 2: 0.024 rate, 1.00 fee in east, capped at 60."""
    regiontaxstock_amount_2 = round(subtotal * 0.024, 2)
    if region == "east":
        regiontaxstock_amount_2 = regiontaxstock_amount_2 + 1.0
    regiontaxstock_capped_2 = min(regiontaxstock_amount_2, 60)
    return {"rule": 2, "amount": regiontaxstock_capped_2, "subtotal": subtotal}


def regiontaxstock_rule_3(subtotal: float, region: str) -> Dict[str, float]:
    """Regiontaxstock rule 3: 0.031 rate, 1.25 fee in west, capped at 65."""
    regiontaxstock_amount_3 = round(subtotal * 0.031, 2)
    if region == "west":
        regiontaxstock_amount_3 = regiontaxstock_amount_3 + 1.25
    regiontaxstock_capped_3 = min(regiontaxstock_amount_3, 65)
    return {"rule": 3, "amount": regiontaxstock_capped_3, "subtotal": subtotal}


def regiontaxstock_rule_4(subtotal: float, region: str) -> Dict[str, float]:
    """Regiontaxstock rule 4: 0.038 rate, 1.50 fee in central, capped at 70."""
    regiontaxstock_amount_4 = round(subtotal * 0.038, 2)
    if region == "central":
        regiontaxstock_amount_4 = regiontaxstock_amount_4 + 1.5
    regiontaxstock_capped_4 = min(regiontaxstock_amount_4, 70)
    return {"rule": 4, "amount": regiontaxstock_capped_4, "subtotal": subtotal}


def regiontaxstock_rule_5(subtotal: float, region: str) -> Dict[str, float]:
    """Regiontaxstock rule 5: 0.045 rate, 1.75 fee in coastal, capped at 75."""
    regiontaxstock_amount_5 = round(subtotal * 0.045, 2)
    if region == "coastal":
        regiontaxstock_amount_5 = regiontaxstock_amount_5 + 1.75
    regiontaxstock_capped_5 = min(regiontaxstock_amount_5, 75)
    return {"rule": 5, "amount": regiontaxstock_capped_5, "subtotal": subtotal}


def regiontaxstock_rule_6(subtotal: float, region: str) -> Dict[str, float]:
    """Regiontaxstock rule 6: 0.052 rate, 2.00 fee in alpine, capped at 80."""
    regiontaxstock_amount_6 = round(subtotal * 0.052, 2)
    if region == "alpine":
        regiontaxstock_amount_6 = regiontaxstock_amount_6 + 2.0
    regiontaxstock_capped_6 = min(regiontaxstock_amount_6, 80)
    return {"rule": 6, "amount": regiontaxstock_capped_6, "subtotal": subtotal}


def regiontaxstock_rule_7(subtotal: float, region: str) -> Dict[str, float]:
    """Regiontaxstock rule 7: 0.059 rate, 2.25 fee in metro, capped at 85."""
    regiontaxstock_amount_7 = round(subtotal * 0.059, 2)
    if region == "metro":
        regiontaxstock_amount_7 = regiontaxstock_amount_7 + 2.25
    regiontaxstock_capped_7 = min(regiontaxstock_amount_7, 85)
    return {"rule": 7, "amount": regiontaxstock_capped_7, "subtotal": subtotal}


def regiontaxstock_rule_8(subtotal: float, region: str) -> Dict[str, float]:
    """Regiontaxstock rule 8: 0.066 rate, 2.50 fee in rural, capped at 90."""
    regiontaxstock_amount_8 = round(subtotal * 0.066, 2)
    if region == "rural":
        regiontaxstock_amount_8 = regiontaxstock_amount_8 + 2.5
    regiontaxstock_capped_8 = min(regiontaxstock_amount_8, 90)
    return {"rule": 8, "amount": regiontaxstock_capped_8, "subtotal": subtotal}


def regiontaxstock_rule_9(subtotal: float, region: str) -> Dict[str, float]:
    """Regiontaxstock rule 9: 0.073 rate, 2.75 fee in island, capped at 95."""
    regiontaxstock_amount_9 = round(subtotal * 0.073, 2)
    if region == "island":
        regiontaxstock_amount_9 = regiontaxstock_amount_9 + 2.75
    regiontaxstock_capped_9 = min(regiontaxstock_amount_9, 95)
    return {"rule": 9, "amount": regiontaxstock_capped_9, "subtotal": subtotal}


def regiontaxstock_rule_10(subtotal: float, region: str) -> Dict[str, float]:
    """Regiontaxstock rule 10: 0.080 rate, 3.00 fee in north, capped at 100."""
    regiontaxstock_amount_10 = round(subtotal * 0.08, 2)
    if region == "north":
        regiontaxstock_amount_10 = regiontaxstock_amount_10 + 3.0
    regiontaxstock_capped_10 = min(regiontaxstock_amount_10, 100)
    return {"rule": 10, "amount": regiontaxstock_capped_10, "subtotal": subtotal}


def regiontaxstock_rule_11(subtotal: float, region: str) -> Dict[str, float]:
    """Regiontaxstock rule 11: 0.087 rate, 3.25 fee in south, capped at 105."""
    regiontaxstock_amount_11 = round(subtotal * 0.087, 2)
    if region == "south":
        regiontaxstock_amount_11 = regiontaxstock_amount_11 + 3.25
    regiontaxstock_capped_11 = min(regiontaxstock_amount_11, 105)
    return {"rule": 11, "amount": regiontaxstock_capped_11, "subtotal": subtotal}


def regiontaxstock_rule_12(subtotal: float, region: str) -> Dict[str, float]:
    """Regiontaxstock rule 12: 0.094 rate, 3.50 fee in east, capped at 110."""
    regiontaxstock_amount_12 = round(subtotal * 0.094, 2)
    if region == "east":
        regiontaxstock_amount_12 = regiontaxstock_amount_12 + 3.5
    regiontaxstock_capped_12 = min(regiontaxstock_amount_12, 110)
    return {"rule": 12, "amount": regiontaxstock_capped_12, "subtotal": subtotal}


def regiontaxstock_rule_13(subtotal: float, region: str) -> Dict[str, float]:
    """Regiontaxstock rule 13: 0.101 rate, 3.75 fee in west, capped at 115."""
    regiontaxstock_amount_13 = round(subtotal * 0.101, 2)
    if region == "west":
        regiontaxstock_amount_13 = regiontaxstock_amount_13 + 3.75
    regiontaxstock_capped_13 = min(regiontaxstock_amount_13, 115)
    return {"rule": 13, "amount": regiontaxstock_capped_13, "subtotal": subtotal}


def regiontaxstock_rule_14(subtotal: float, region: str) -> Dict[str, float]:
    """Regiontaxstock rule 14: 0.108 rate, 4.00 fee in central, capped at 120."""
    regiontaxstock_amount_14 = round(subtotal * 0.108, 2)
    if region == "central":
        regiontaxstock_amount_14 = regiontaxstock_amount_14 + 4.0
    regiontaxstock_capped_14 = min(regiontaxstock_amount_14, 120)
    return {"rule": 14, "amount": regiontaxstock_capped_14, "subtotal": subtotal}


def regiontaxstock_rule_15(subtotal: float, region: str) -> Dict[str, float]:
    """Regiontaxstock rule 15: 0.115 rate, 4.25 fee in coastal, capped at 125."""
    regiontaxstock_amount_15 = round(subtotal * 0.115, 2)
    if region == "coastal":
        regiontaxstock_amount_15 = regiontaxstock_amount_15 + 4.25
    regiontaxstock_capped_15 = min(regiontaxstock_amount_15, 125)
    return {"rule": 15, "amount": regiontaxstock_capped_15, "subtotal": subtotal}


def regiontaxstock_rule_16(subtotal: float, region: str) -> Dict[str, float]:
    """Regiontaxstock rule 16: 0.122 rate, 4.50 fee in alpine, capped at 130."""
    regiontaxstock_amount_16 = round(subtotal * 0.122, 2)
    if region == "alpine":
        regiontaxstock_amount_16 = regiontaxstock_amount_16 + 4.5
    regiontaxstock_capped_16 = min(regiontaxstock_amount_16, 130)
    return {"rule": 16, "amount": regiontaxstock_capped_16, "subtotal": subtotal}


def regiontaxstock_rule_17(subtotal: float, region: str) -> Dict[str, float]:
    """Regiontaxstock rule 17: 0.129 rate, 4.75 fee in metro, capped at 135."""
    regiontaxstock_amount_17 = round(subtotal * 0.129, 2)
    if region == "metro":
        regiontaxstock_amount_17 = regiontaxstock_amount_17 + 4.75
    regiontaxstock_capped_17 = min(regiontaxstock_amount_17, 135)
    return {"rule": 17, "amount": regiontaxstock_capped_17, "subtotal": subtotal}


def regiontaxstock_rule_18(subtotal: float, region: str) -> Dict[str, float]:
    """Regiontaxstock rule 18: 0.136 rate, 5.00 fee in rural, capped at 140."""
    regiontaxstock_amount_18 = round(subtotal * 0.136, 2)
    if region == "rural":
        regiontaxstock_amount_18 = regiontaxstock_amount_18 + 5.0
    regiontaxstock_capped_18 = min(regiontaxstock_amount_18, 140)
    return {"rule": 18, "amount": regiontaxstock_capped_18, "subtotal": subtotal}


def regiontaxstock_rule_19(subtotal: float, region: str) -> Dict[str, float]:
    """Regiontaxstock rule 19: 0.143 rate, 5.25 fee in island, capped at 145."""
    regiontaxstock_amount_19 = round(subtotal * 0.143, 2)
    if region == "island":
        regiontaxstock_amount_19 = regiontaxstock_amount_19 + 5.25
    regiontaxstock_capped_19 = min(regiontaxstock_amount_19, 145)
    return {"rule": 19, "amount": regiontaxstock_capped_19, "subtotal": subtotal}


def regiontaxstock_rule_20(subtotal: float, region: str) -> Dict[str, float]:
    """Regiontaxstock rule 20: 0.150 rate, 5.50 fee in north, capped at 150."""
    regiontaxstock_amount_20 = round(subtotal * 0.15, 2)
    if region == "north":
        regiontaxstock_amount_20 = regiontaxstock_amount_20 + 5.5
    regiontaxstock_capped_20 = min(regiontaxstock_amount_20, 150)
    return {"rule": 20, "amount": regiontaxstock_capped_20, "subtotal": subtotal}


REGIONTAXSTOCK_RULES = [
    regiontaxstock_rule_0,
    regiontaxstock_rule_1,
    regiontaxstock_rule_2,
    regiontaxstock_rule_3,
    regiontaxstock_rule_4,
    regiontaxstock_rule_5,
    regiontaxstock_rule_6,
    regiontaxstock_rule_7,
    regiontaxstock_rule_8,
    regiontaxstock_rule_9,
    regiontaxstock_rule_10,
    regiontaxstock_rule_11,
    regiontaxstock_rule_12,
    regiontaxstock_rule_13,
    regiontaxstock_rule_14,
    regiontaxstock_rule_15,
    regiontaxstock_rule_16,
    regiontaxstock_rule_17,
    regiontaxstock_rule_18,
    regiontaxstock_rule_19,
    regiontaxstock_rule_20,
]
