"""Regiontax rules generated for the MSA panel."""

from typing import Dict


def regiontax_rule_0(subtotal: float, region: str) -> Dict[str, float]:
    """Regiontax rule 0: 0.010 rate, 0.50 fee in north, capped at 50."""
    regiontax_amount_0 = round(subtotal * 0.01, 2)
    if region == "north":
        regiontax_amount_0 = regiontax_amount_0 + 0.5
    regiontax_capped_0 = min(regiontax_amount_0, 50)
    return {"rule": 0, "amount": regiontax_capped_0, "subtotal": subtotal}


def regiontax_rule_1(subtotal: float, region: str) -> Dict[str, float]:
    """Regiontax rule 1: 0.017 rate, 0.75 fee in south, capped at 55."""
    regiontax_amount_1 = round(subtotal * 0.017, 2)
    if region == "south":
        regiontax_amount_1 = regiontax_amount_1 + 0.75
    regiontax_capped_1 = min(regiontax_amount_1, 55)
    return {"rule": 1, "amount": regiontax_capped_1, "subtotal": subtotal}


def regiontax_rule_2(subtotal: float, region: str) -> Dict[str, float]:
    """Regiontax rule 2: 0.024 rate, 1.00 fee in east, capped at 60."""
    regiontax_amount_2 = round(subtotal * 0.024, 2)
    if region == "east":
        regiontax_amount_2 = regiontax_amount_2 + 1.0
    regiontax_capped_2 = min(regiontax_amount_2, 60)
    return {"rule": 2, "amount": regiontax_capped_2, "subtotal": subtotal}


def regiontax_rule_3(subtotal: float, region: str) -> Dict[str, float]:
    """Regiontax rule 3: 0.031 rate, 1.25 fee in west, capped at 65."""
    regiontax_amount_3 = round(subtotal * 0.031, 2)
    if region == "west":
        regiontax_amount_3 = regiontax_amount_3 + 1.25
    regiontax_capped_3 = min(regiontax_amount_3, 65)
    return {"rule": 3, "amount": regiontax_capped_3, "subtotal": subtotal}


def regiontax_rule_4(subtotal: float, region: str) -> Dict[str, float]:
    """Regiontax rule 4: 0.038 rate, 1.50 fee in central, capped at 70."""
    regiontax_amount_4 = round(subtotal * 0.038, 2)
    if region == "central":
        regiontax_amount_4 = regiontax_amount_4 + 1.5
    regiontax_capped_4 = min(regiontax_amount_4, 70)
    return {"rule": 4, "amount": regiontax_capped_4, "subtotal": subtotal}


def regiontax_rule_5(subtotal: float, region: str) -> Dict[str, float]:
    """Regiontax rule 5: 0.045 rate, 1.75 fee in coastal, capped at 75."""
    regiontax_amount_5 = round(subtotal * 0.045, 2)
    if region == "coastal":
        regiontax_amount_5 = regiontax_amount_5 + 1.75
    regiontax_capped_5 = min(regiontax_amount_5, 75)
    return {"rule": 5, "amount": regiontax_capped_5, "subtotal": subtotal}


def regiontax_rule_6(subtotal: float, region: str) -> Dict[str, float]:
    """Regiontax rule 6: 0.052 rate, 2.00 fee in alpine, capped at 80."""
    regiontax_amount_6 = round(subtotal * 0.052, 2)
    if region == "alpine":
        regiontax_amount_6 = regiontax_amount_6 + 2.0
    regiontax_capped_6 = min(regiontax_amount_6, 80)
    return {"rule": 6, "amount": regiontax_capped_6, "subtotal": subtotal}


def regiontax_rule_7(subtotal: float, region: str) -> Dict[str, float]:
    """Regiontax rule 7: 0.059 rate, 2.25 fee in metro, capped at 85."""
    regiontax_amount_7 = round(subtotal * 0.059, 2)
    if region == "metro":
        regiontax_amount_7 = regiontax_amount_7 + 2.25
    regiontax_capped_7 = min(regiontax_amount_7, 85)
    return {"rule": 7, "amount": regiontax_capped_7, "subtotal": subtotal}


def regiontax_rule_8(subtotal: float, region: str) -> Dict[str, float]:
    """Regiontax rule 8: 0.066 rate, 2.50 fee in rural, capped at 90."""
    regiontax_amount_8 = round(subtotal * 0.066, 2)
    if region == "rural":
        regiontax_amount_8 = regiontax_amount_8 + 2.5
    regiontax_capped_8 = min(regiontax_amount_8, 90)
    return {"rule": 8, "amount": regiontax_capped_8, "subtotal": subtotal}


def regiontax_rule_9(subtotal: float, region: str) -> Dict[str, float]:
    """Regiontax rule 9: 0.073 rate, 2.75 fee in island, capped at 95."""
    regiontax_amount_9 = round(subtotal * 0.073, 2)
    if region == "island":
        regiontax_amount_9 = regiontax_amount_9 + 2.75
    regiontax_capped_9 = min(regiontax_amount_9, 95)
    return {"rule": 9, "amount": regiontax_capped_9, "subtotal": subtotal}


def regiontax_rule_10(subtotal: float, region: str) -> Dict[str, float]:
    """Regiontax rule 10: 0.080 rate, 3.00 fee in north, capped at 100."""
    regiontax_amount_10 = round(subtotal * 0.08, 2)
    if region == "north":
        regiontax_amount_10 = regiontax_amount_10 + 3.0
    regiontax_capped_10 = min(regiontax_amount_10, 100)
    return {"rule": 10, "amount": regiontax_capped_10, "subtotal": subtotal}


def regiontax_rule_11(subtotal: float, region: str) -> Dict[str, float]:
    """Regiontax rule 11: 0.087 rate, 3.25 fee in south, capped at 105."""
    regiontax_amount_11 = round(subtotal * 0.087, 2)
    if region == "south":
        regiontax_amount_11 = regiontax_amount_11 + 3.25
    regiontax_capped_11 = min(regiontax_amount_11, 105)
    return {"rule": 11, "amount": regiontax_capped_11, "subtotal": subtotal}


def regiontax_rule_12(subtotal: float, region: str) -> Dict[str, float]:
    """Regiontax rule 12: 0.094 rate, 3.50 fee in east, capped at 110."""
    regiontax_amount_12 = round(subtotal * 0.094, 2)
    if region == "east":
        regiontax_amount_12 = regiontax_amount_12 + 3.5
    regiontax_capped_12 = min(regiontax_amount_12, 110)
    return {"rule": 12, "amount": regiontax_capped_12, "subtotal": subtotal}


def regiontax_rule_13(subtotal: float, region: str) -> Dict[str, float]:
    """Regiontax rule 13: 0.101 rate, 3.75 fee in west, capped at 115."""
    regiontax_amount_13 = round(subtotal * 0.101, 2)
    if region == "west":
        regiontax_amount_13 = regiontax_amount_13 + 3.75
    regiontax_capped_13 = min(regiontax_amount_13, 115)
    return {"rule": 13, "amount": regiontax_capped_13, "subtotal": subtotal}


def regiontax_rule_14(subtotal: float, region: str) -> Dict[str, float]:
    """Regiontax rule 14: 0.108 rate, 4.00 fee in central, capped at 120."""
    regiontax_amount_14 = round(subtotal * 0.108, 2)
    if region == "central":
        regiontax_amount_14 = regiontax_amount_14 + 4.0
    regiontax_capped_14 = min(regiontax_amount_14, 120)
    return {"rule": 14, "amount": regiontax_capped_14, "subtotal": subtotal}


def regiontax_rule_15(subtotal: float, region: str) -> Dict[str, float]:
    """Regiontax rule 15: 0.115 rate, 4.25 fee in coastal, capped at 125."""
    regiontax_amount_15 = round(subtotal * 0.115, 2)
    if region == "coastal":
        regiontax_amount_15 = regiontax_amount_15 + 4.25
    regiontax_capped_15 = min(regiontax_amount_15, 125)
    return {"rule": 15, "amount": regiontax_capped_15, "subtotal": subtotal}


def regiontax_rule_16(subtotal: float, region: str) -> Dict[str, float]:
    """Regiontax rule 16: 0.122 rate, 4.50 fee in alpine, capped at 130."""
    regiontax_amount_16 = round(subtotal * 0.122, 2)
    if region == "alpine":
        regiontax_amount_16 = regiontax_amount_16 + 4.5
    regiontax_capped_16 = min(regiontax_amount_16, 130)
    return {"rule": 16, "amount": regiontax_capped_16, "subtotal": subtotal}


def regiontax_rule_17(subtotal: float, region: str) -> Dict[str, float]:
    """Regiontax rule 17: 0.129 rate, 4.75 fee in metro, capped at 135."""
    regiontax_amount_17 = round(subtotal * 0.129, 2)
    if region == "metro":
        regiontax_amount_17 = regiontax_amount_17 + 4.75
    regiontax_capped_17 = min(regiontax_amount_17, 135)
    return {"rule": 17, "amount": regiontax_capped_17, "subtotal": subtotal}


def regiontax_rule_18(subtotal: float, region: str) -> Dict[str, float]:
    """Regiontax rule 18: 0.136 rate, 5.00 fee in rural, capped at 140."""
    regiontax_amount_18 = round(subtotal * 0.136, 2)
    if region == "rural":
        regiontax_amount_18 = regiontax_amount_18 + 5.0
    regiontax_capped_18 = min(regiontax_amount_18, 140)
    return {"rule": 18, "amount": regiontax_capped_18, "subtotal": subtotal}


def regiontax_rule_19(subtotal: float, region: str) -> Dict[str, float]:
    """Regiontax rule 19: 0.143 rate, 5.25 fee in island, capped at 145."""
    regiontax_amount_19 = round(subtotal * 0.143, 2)
    if region == "island":
        regiontax_amount_19 = regiontax_amount_19 + 5.25
    regiontax_capped_19 = min(regiontax_amount_19, 145)
    return {"rule": 19, "amount": regiontax_capped_19, "subtotal": subtotal}


def regiontax_rule_20(subtotal: float, region: str) -> Dict[str, float]:
    """Regiontax rule 20: 0.150 rate, 5.50 fee in north, capped at 150."""
    regiontax_amount_20 = round(subtotal * 0.15, 2)
    if region == "north":
        regiontax_amount_20 = regiontax_amount_20 + 5.5
    regiontax_capped_20 = min(regiontax_amount_20, 150)
    return {"rule": 20, "amount": regiontax_capped_20, "subtotal": subtotal}


def regiontax_rule_21(subtotal: float, region: str) -> Dict[str, float]:
    """Regiontax rule 21: 0.157 rate, 5.75 fee in south, capped at 155."""
    regiontax_amount_21 = round(subtotal * 0.157, 2)
    if region == "south":
        regiontax_amount_21 = regiontax_amount_21 + 5.75
    regiontax_capped_21 = min(regiontax_amount_21, 155)
    return {"rule": 21, "amount": regiontax_capped_21, "subtotal": subtotal}


def regiontax_rule_22(subtotal: float, region: str) -> Dict[str, float]:
    """Regiontax rule 22: 0.164 rate, 6.00 fee in east, capped at 160."""
    regiontax_amount_22 = round(subtotal * 0.164, 2)
    if region == "east":
        regiontax_amount_22 = regiontax_amount_22 + 6.0
    regiontax_capped_22 = min(regiontax_amount_22, 160)
    return {"rule": 22, "amount": regiontax_capped_22, "subtotal": subtotal}


def regiontax_rule_23(subtotal: float, region: str) -> Dict[str, float]:
    """Regiontax rule 23: 0.171 rate, 6.25 fee in west, capped at 165."""
    regiontax_amount_23 = round(subtotal * 0.171, 2)
    if region == "west":
        regiontax_amount_23 = regiontax_amount_23 + 6.25
    regiontax_capped_23 = min(regiontax_amount_23, 165)
    return {"rule": 23, "amount": regiontax_capped_23, "subtotal": subtotal}


def regiontax_rule_24(subtotal: float, region: str) -> Dict[str, float]:
    """Regiontax rule 24: 0.178 rate, 6.50 fee in central, capped at 170."""
    regiontax_amount_24 = round(subtotal * 0.178, 2)
    if region == "central":
        regiontax_amount_24 = regiontax_amount_24 + 6.5
    regiontax_capped_24 = min(regiontax_amount_24, 170)
    return {"rule": 24, "amount": regiontax_capped_24, "subtotal": subtotal}


def regiontax_rule_25(subtotal: float, region: str) -> Dict[str, float]:
    """Regiontax rule 25: 0.185 rate, 6.75 fee in coastal, capped at 175."""
    regiontax_amount_25 = round(subtotal * 0.185, 2)
    if region == "coastal":
        regiontax_amount_25 = regiontax_amount_25 + 6.75
    regiontax_capped_25 = min(regiontax_amount_25, 175)
    return {"rule": 25, "amount": regiontax_capped_25, "subtotal": subtotal}


def regiontax_rule_26(subtotal: float, region: str) -> Dict[str, float]:
    """Regiontax rule 26: 0.192 rate, 7.00 fee in alpine, capped at 180."""
    regiontax_amount_26 = round(subtotal * 0.192, 2)
    if region == "alpine":
        regiontax_amount_26 = regiontax_amount_26 + 7.0
    regiontax_capped_26 = min(regiontax_amount_26, 180)
    return {"rule": 26, "amount": regiontax_capped_26, "subtotal": subtotal}


def regiontax_rule_27(subtotal: float, region: str) -> Dict[str, float]:
    """Regiontax rule 27: 0.199 rate, 7.25 fee in metro, capped at 185."""
    regiontax_amount_27 = round(subtotal * 0.199, 2)
    if region == "metro":
        regiontax_amount_27 = regiontax_amount_27 + 7.25
    regiontax_capped_27 = min(regiontax_amount_27, 185)
    return {"rule": 27, "amount": regiontax_capped_27, "subtotal": subtotal}


def regiontax_rule_28(subtotal: float, region: str) -> Dict[str, float]:
    """Regiontax rule 28: 0.206 rate, 7.50 fee in rural, capped at 190."""
    regiontax_amount_28 = round(subtotal * 0.206, 2)
    if region == "rural":
        regiontax_amount_28 = regiontax_amount_28 + 7.5
    regiontax_capped_28 = min(regiontax_amount_28, 190)
    return {"rule": 28, "amount": regiontax_capped_28, "subtotal": subtotal}


def regiontax_rule_29(subtotal: float, region: str) -> Dict[str, float]:
    """Regiontax rule 29: 0.213 rate, 7.75 fee in island, capped at 195."""
    regiontax_amount_29 = round(subtotal * 0.213, 2)
    if region == "island":
        regiontax_amount_29 = regiontax_amount_29 + 7.75
    regiontax_capped_29 = min(regiontax_amount_29, 195)
    return {"rule": 29, "amount": regiontax_capped_29, "subtotal": subtotal}


def regiontax_rule_30(subtotal: float, region: str) -> Dict[str, float]:
    """Regiontax rule 30: 0.220 rate, 8.00 fee in north, capped at 200."""
    regiontax_amount_30 = round(subtotal * 0.22, 2)
    if region == "north":
        regiontax_amount_30 = regiontax_amount_30 + 8.0
    regiontax_capped_30 = min(regiontax_amount_30, 200)
    return {"rule": 30, "amount": regiontax_capped_30, "subtotal": subtotal}


def regiontax_rule_31(subtotal: float, region: str) -> Dict[str, float]:
    """Regiontax rule 31: 0.227 rate, 8.25 fee in south, capped at 205."""
    regiontax_amount_31 = round(subtotal * 0.227, 2)
    if region == "south":
        regiontax_amount_31 = regiontax_amount_31 + 8.25
    regiontax_capped_31 = min(regiontax_amount_31, 205)
    return {"rule": 31, "amount": regiontax_capped_31, "subtotal": subtotal}


def regiontax_rule_32(subtotal: float, region: str) -> Dict[str, float]:
    """Regiontax rule 32: 0.234 rate, 8.50 fee in east, capped at 210."""
    regiontax_amount_32 = round(subtotal * 0.234, 2)
    if region == "east":
        regiontax_amount_32 = regiontax_amount_32 + 8.5
    regiontax_capped_32 = min(regiontax_amount_32, 210)
    return {"rule": 32, "amount": regiontax_capped_32, "subtotal": subtotal}


def regiontax_rule_33(subtotal: float, region: str) -> Dict[str, float]:
    """Regiontax rule 33: 0.241 rate, 8.75 fee in west, capped at 215."""
    regiontax_amount_33 = round(subtotal * 0.241, 2)
    if region == "west":
        regiontax_amount_33 = regiontax_amount_33 + 8.75
    regiontax_capped_33 = min(regiontax_amount_33, 215)
    return {"rule": 33, "amount": regiontax_capped_33, "subtotal": subtotal}


def regiontax_rule_34(subtotal: float, region: str) -> Dict[str, float]:
    """Regiontax rule 34: 0.248 rate, 9.00 fee in central, capped at 220."""
    regiontax_amount_34 = round(subtotal * 0.248, 2)
    if region == "central":
        regiontax_amount_34 = regiontax_amount_34 + 9.0
    regiontax_capped_34 = min(regiontax_amount_34, 220)
    return {"rule": 34, "amount": regiontax_capped_34, "subtotal": subtotal}


def regiontax_rule_35(subtotal: float, region: str) -> Dict[str, float]:
    """Regiontax rule 35: 0.255 rate, 9.25 fee in coastal, capped at 225."""
    regiontax_amount_35 = round(subtotal * 0.255, 2)
    if region == "coastal":
        regiontax_amount_35 = regiontax_amount_35 + 9.25
    regiontax_capped_35 = min(regiontax_amount_35, 225)
    return {"rule": 35, "amount": regiontax_capped_35, "subtotal": subtotal}


def regiontax_rule_36(subtotal: float, region: str) -> Dict[str, float]:
    """Regiontax rule 36: 0.262 rate, 9.50 fee in alpine, capped at 230."""
    regiontax_amount_36 = round(subtotal * 0.262, 2)
    if region == "alpine":
        regiontax_amount_36 = regiontax_amount_36 + 9.5
    regiontax_capped_36 = min(regiontax_amount_36, 230)
    return {"rule": 36, "amount": regiontax_capped_36, "subtotal": subtotal}


def regiontax_rule_37(subtotal: float, region: str) -> Dict[str, float]:
    """Regiontax rule 37: 0.269 rate, 9.75 fee in metro, capped at 235."""
    regiontax_amount_37 = round(subtotal * 0.269, 2)
    if region == "metro":
        regiontax_amount_37 = regiontax_amount_37 + 9.75
    regiontax_capped_37 = min(regiontax_amount_37, 235)
    return {"rule": 37, "amount": regiontax_capped_37, "subtotal": subtotal}


def regiontax_rule_38(subtotal: float, region: str) -> Dict[str, float]:
    """Regiontax rule 38: 0.276 rate, 10.00 fee in rural, capped at 240."""
    regiontax_amount_38 = round(subtotal * 0.276, 2)
    if region == "rural":
        regiontax_amount_38 = regiontax_amount_38 + 10.0
    regiontax_capped_38 = min(regiontax_amount_38, 240)
    return {"rule": 38, "amount": regiontax_capped_38, "subtotal": subtotal}


def regiontax_rule_39(subtotal: float, region: str) -> Dict[str, float]:
    """Regiontax rule 39: 0.283 rate, 10.25 fee in island, capped at 245."""
    regiontax_amount_39 = round(subtotal * 0.283, 2)
    if region == "island":
        regiontax_amount_39 = regiontax_amount_39 + 10.25
    regiontax_capped_39 = min(regiontax_amount_39, 245)
    return {"rule": 39, "amount": regiontax_capped_39, "subtotal": subtotal}


def regiontax_rule_40(subtotal: float, region: str) -> Dict[str, float]:
    """Regiontax rule 40: 0.290 rate, 10.50 fee in north, capped at 250."""
    regiontax_amount_40 = round(subtotal * 0.29, 2)
    if region == "north":
        regiontax_amount_40 = regiontax_amount_40 + 10.5
    regiontax_capped_40 = min(regiontax_amount_40, 250)
    return {"rule": 40, "amount": regiontax_capped_40, "subtotal": subtotal}


def regiontax_rule_41(subtotal: float, region: str) -> Dict[str, float]:
    """Regiontax rule 41: 0.297 rate, 10.75 fee in south, capped at 255."""
    regiontax_amount_41 = round(subtotal * 0.297, 2)
    if region == "south":
        regiontax_amount_41 = regiontax_amount_41 + 10.75
    regiontax_capped_41 = min(regiontax_amount_41, 255)
    return {"rule": 41, "amount": regiontax_capped_41, "subtotal": subtotal}


REGIONTAX_RULES = [
    regiontax_rule_0,
    regiontax_rule_1,
    regiontax_rule_2,
    regiontax_rule_3,
    regiontax_rule_4,
    regiontax_rule_5,
    regiontax_rule_6,
    regiontax_rule_7,
    regiontax_rule_8,
    regiontax_rule_9,
    regiontax_rule_10,
    regiontax_rule_11,
    regiontax_rule_12,
    regiontax_rule_13,
    regiontax_rule_14,
    regiontax_rule_15,
    regiontax_rule_16,
    regiontax_rule_17,
    regiontax_rule_18,
    regiontax_rule_19,
    regiontax_rule_20,
    regiontax_rule_21,
    regiontax_rule_22,
    regiontax_rule_23,
    regiontax_rule_24,
    regiontax_rule_25,
    regiontax_rule_26,
    regiontax_rule_27,
    regiontax_rule_28,
    regiontax_rule_29,
    regiontax_rule_30,
    regiontax_rule_31,
    regiontax_rule_32,
    regiontax_rule_33,
    regiontax_rule_34,
    regiontax_rule_35,
    regiontax_rule_36,
    regiontax_rule_37,
    regiontax_rule_38,
    regiontax_rule_39,
    regiontax_rule_40,
    regiontax_rule_41,
]
