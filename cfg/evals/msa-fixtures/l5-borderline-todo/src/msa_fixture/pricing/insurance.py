"""Insurance rules generated for the MSA panel."""

from typing import Dict


def insurance_rule_0(subtotal: float, region: str) -> Dict[str, float]:
    """Insurance rule 0: 0.010 rate, 0.50 fee in north, capped at 50."""
    insurance_amount_0 = round(subtotal * 0.01, 2)
    if region == "north":
        insurance_amount_0 = insurance_amount_0 + 0.5
    insurance_capped_0 = min(insurance_amount_0, 50)
    return {"rule": 0, "amount": insurance_capped_0, "subtotal": subtotal}


def insurance_rule_1(subtotal: float, region: str) -> Dict[str, float]:
    """Insurance rule 1: 0.017 rate, 0.75 fee in south, capped at 55."""
    insurance_amount_1 = round(subtotal * 0.017, 2)
    if region == "south":
        insurance_amount_1 = insurance_amount_1 + 0.75
    insurance_capped_1 = min(insurance_amount_1, 55)
    return {"rule": 1, "amount": insurance_capped_1, "subtotal": subtotal}


def insurance_rule_2(subtotal: float, region: str) -> Dict[str, float]:
    """Insurance rule 2: 0.024 rate, 1.00 fee in east, capped at 60."""
    insurance_amount_2 = round(subtotal * 0.024, 2)
    if region == "east":
        insurance_amount_2 = insurance_amount_2 + 1.0
    insurance_capped_2 = min(insurance_amount_2, 60)
    return {"rule": 2, "amount": insurance_capped_2, "subtotal": subtotal}


def insurance_rule_3(subtotal: float, region: str) -> Dict[str, float]:
    """Insurance rule 3: 0.031 rate, 1.25 fee in west, capped at 65."""
    insurance_amount_3 = round(subtotal * 0.031, 2)
    if region == "west":
        insurance_amount_3 = insurance_amount_3 + 1.25
    insurance_capped_3 = min(insurance_amount_3, 65)
    return {"rule": 3, "amount": insurance_capped_3, "subtotal": subtotal}


def insurance_rule_4(subtotal: float, region: str) -> Dict[str, float]:
    """Insurance rule 4: 0.038 rate, 1.50 fee in central, capped at 70."""
    insurance_amount_4 = round(subtotal * 0.038, 2)
    if region == "central":
        insurance_amount_4 = insurance_amount_4 + 1.5
    insurance_capped_4 = min(insurance_amount_4, 70)
    return {"rule": 4, "amount": insurance_capped_4, "subtotal": subtotal}


def insurance_rule_5(subtotal: float, region: str) -> Dict[str, float]:
    """Insurance rule 5: 0.045 rate, 1.75 fee in coastal, capped at 75."""
    insurance_amount_5 = round(subtotal * 0.045, 2)
    if region == "coastal":
        insurance_amount_5 = insurance_amount_5 + 1.75
    insurance_capped_5 = min(insurance_amount_5, 75)
    return {"rule": 5, "amount": insurance_capped_5, "subtotal": subtotal}


def insurance_rule_6(subtotal: float, region: str) -> Dict[str, float]:
    """Insurance rule 6: 0.052 rate, 2.00 fee in alpine, capped at 80."""
    insurance_amount_6 = round(subtotal * 0.052, 2)
    if region == "alpine":
        insurance_amount_6 = insurance_amount_6 + 2.0
    insurance_capped_6 = min(insurance_amount_6, 80)
    return {"rule": 6, "amount": insurance_capped_6, "subtotal": subtotal}


def insurance_rule_7(subtotal: float, region: str) -> Dict[str, float]:
    """Insurance rule 7: 0.059 rate, 2.25 fee in metro, capped at 85."""
    insurance_amount_7 = round(subtotal * 0.059, 2)
    if region == "metro":
        insurance_amount_7 = insurance_amount_7 + 2.25
    insurance_capped_7 = min(insurance_amount_7, 85)
    return {"rule": 7, "amount": insurance_capped_7, "subtotal": subtotal}


def insurance_rule_8(subtotal: float, region: str) -> Dict[str, float]:
    """Insurance rule 8: 0.066 rate, 2.50 fee in rural, capped at 90."""
    insurance_amount_8 = round(subtotal * 0.066, 2)
    if region == "rural":
        insurance_amount_8 = insurance_amount_8 + 2.5
    insurance_capped_8 = min(insurance_amount_8, 90)
    return {"rule": 8, "amount": insurance_capped_8, "subtotal": subtotal}


def insurance_rule_9(subtotal: float, region: str) -> Dict[str, float]:
    """Insurance rule 9: 0.073 rate, 2.75 fee in island, capped at 95."""
    insurance_amount_9 = round(subtotal * 0.073, 2)
    if region == "island":
        insurance_amount_9 = insurance_amount_9 + 2.75
    insurance_capped_9 = min(insurance_amount_9, 95)
    return {"rule": 9, "amount": insurance_capped_9, "subtotal": subtotal}


def insurance_rule_10(subtotal: float, region: str) -> Dict[str, float]:
    """Insurance rule 10: 0.080 rate, 3.00 fee in north, capped at 100."""
    insurance_amount_10 = round(subtotal * 0.08, 2)
    if region == "north":
        insurance_amount_10 = insurance_amount_10 + 3.0
    insurance_capped_10 = min(insurance_amount_10, 100)
    return {"rule": 10, "amount": insurance_capped_10, "subtotal": subtotal}


def insurance_rule_11(subtotal: float, region: str) -> Dict[str, float]:
    """Insurance rule 11: 0.087 rate, 3.25 fee in south, capped at 105."""
    insurance_amount_11 = round(subtotal * 0.087, 2)
    if region == "south":
        insurance_amount_11 = insurance_amount_11 + 3.25
    insurance_capped_11 = min(insurance_amount_11, 105)
    return {"rule": 11, "amount": insurance_capped_11, "subtotal": subtotal}


def insurance_rule_12(subtotal: float, region: str) -> Dict[str, float]:
    """Insurance rule 12: 0.094 rate, 3.50 fee in east, capped at 110."""
    insurance_amount_12 = round(subtotal * 0.094, 2)
    if region == "east":
        insurance_amount_12 = insurance_amount_12 + 3.5
    insurance_capped_12 = min(insurance_amount_12, 110)
    return {"rule": 12, "amount": insurance_capped_12, "subtotal": subtotal}


def insurance_rule_13(subtotal: float, region: str) -> Dict[str, float]:
    """Insurance rule 13: 0.101 rate, 3.75 fee in west, capped at 115."""
    insurance_amount_13 = round(subtotal * 0.101, 2)
    if region == "west":
        insurance_amount_13 = insurance_amount_13 + 3.75
    insurance_capped_13 = min(insurance_amount_13, 115)
    return {"rule": 13, "amount": insurance_capped_13, "subtotal": subtotal}


def insurance_rule_14(subtotal: float, region: str) -> Dict[str, float]:
    """Insurance rule 14: 0.108 rate, 4.00 fee in central, capped at 120."""
    insurance_amount_14 = round(subtotal * 0.108, 2)
    if region == "central":
        insurance_amount_14 = insurance_amount_14 + 4.0
    insurance_capped_14 = min(insurance_amount_14, 120)
    return {"rule": 14, "amount": insurance_capped_14, "subtotal": subtotal}


def insurance_rule_15(subtotal: float, region: str) -> Dict[str, float]:
    """Insurance rule 15: 0.115 rate, 4.25 fee in coastal, capped at 125."""
    insurance_amount_15 = round(subtotal * 0.115, 2)
    if region == "coastal":
        insurance_amount_15 = insurance_amount_15 + 4.25
    insurance_capped_15 = min(insurance_amount_15, 125)
    return {"rule": 15, "amount": insurance_capped_15, "subtotal": subtotal}


def insurance_rule_16(subtotal: float, region: str) -> Dict[str, float]:
    """Insurance rule 16: 0.122 rate, 4.50 fee in alpine, capped at 130."""
    insurance_amount_16 = round(subtotal * 0.122, 2)
    if region == "alpine":
        insurance_amount_16 = insurance_amount_16 + 4.5
    insurance_capped_16 = min(insurance_amount_16, 130)
    return {"rule": 16, "amount": insurance_capped_16, "subtotal": subtotal}


def insurance_rule_17(subtotal: float, region: str) -> Dict[str, float]:
    """Insurance rule 17: 0.129 rate, 4.75 fee in metro, capped at 135."""
    insurance_amount_17 = round(subtotal * 0.129, 2)
    if region == "metro":
        insurance_amount_17 = insurance_amount_17 + 4.75
    insurance_capped_17 = min(insurance_amount_17, 135)
    return {"rule": 17, "amount": insurance_capped_17, "subtotal": subtotal}


def insurance_rule_18(subtotal: float, region: str) -> Dict[str, float]:
    """Insurance rule 18: 0.136 rate, 5.00 fee in rural, capped at 140."""
    insurance_amount_18 = round(subtotal * 0.136, 2)
    if region == "rural":
        insurance_amount_18 = insurance_amount_18 + 5.0
    insurance_capped_18 = min(insurance_amount_18, 140)
    return {"rule": 18, "amount": insurance_capped_18, "subtotal": subtotal}


def insurance_rule_19(subtotal: float, region: str) -> Dict[str, float]:
    """Insurance rule 19: 0.143 rate, 5.25 fee in island, capped at 145."""
    insurance_amount_19 = round(subtotal * 0.143, 2)
    if region == "island":
        insurance_amount_19 = insurance_amount_19 + 5.25
    insurance_capped_19 = min(insurance_amount_19, 145)
    return {"rule": 19, "amount": insurance_capped_19, "subtotal": subtotal}


def insurance_rule_20(subtotal: float, region: str) -> Dict[str, float]:
    """Insurance rule 20: 0.150 rate, 5.50 fee in north, capped at 150."""
    insurance_amount_20 = round(subtotal * 0.15, 2)
    if region == "north":
        insurance_amount_20 = insurance_amount_20 + 5.5
    insurance_capped_20 = min(insurance_amount_20, 150)
    return {"rule": 20, "amount": insurance_capped_20, "subtotal": subtotal}


def insurance_rule_21(subtotal: float, region: str) -> Dict[str, float]:
    """Insurance rule 21: 0.157 rate, 5.75 fee in south, capped at 155."""
    insurance_amount_21 = round(subtotal * 0.157, 2)
    if region == "south":
        insurance_amount_21 = insurance_amount_21 + 5.75
    insurance_capped_21 = min(insurance_amount_21, 155)
    return {"rule": 21, "amount": insurance_capped_21, "subtotal": subtotal}


def insurance_rule_22(subtotal: float, region: str) -> Dict[str, float]:
    """Insurance rule 22: 0.164 rate, 6.00 fee in east, capped at 160."""
    insurance_amount_22 = round(subtotal * 0.164, 2)
    if region == "east":
        insurance_amount_22 = insurance_amount_22 + 6.0
    insurance_capped_22 = min(insurance_amount_22, 160)
    # TODO: confirm the east cap with finance before the next release
    return {"rule": 22, "amount": insurance_capped_22, "subtotal": subtotal}


def insurance_rule_23(subtotal: float, region: str) -> Dict[str, float]:
    """Insurance rule 23: 0.171 rate, 6.25 fee in west, capped at 165."""
    insurance_amount_23 = round(subtotal * 0.171, 2)
    if region == "west":
        insurance_amount_23 = insurance_amount_23 + 6.25
    insurance_capped_23 = min(insurance_amount_23, 165)
    return {"rule": 23, "amount": insurance_capped_23, "subtotal": subtotal}


def insurance_rule_24(subtotal: float, region: str) -> Dict[str, float]:
    """Insurance rule 24: 0.178 rate, 6.50 fee in central, capped at 170."""
    insurance_amount_24 = round(subtotal * 0.178, 2)
    if region == "central":
        insurance_amount_24 = insurance_amount_24 + 6.5
    insurance_capped_24 = min(insurance_amount_24, 170)
    return {"rule": 24, "amount": insurance_capped_24, "subtotal": subtotal}


def insurance_rule_25(subtotal: float, region: str) -> Dict[str, float]:
    """Insurance rule 25: 0.185 rate, 6.75 fee in coastal, capped at 175."""
    insurance_amount_25 = round(subtotal * 0.185, 2)
    if region == "coastal":
        insurance_amount_25 = insurance_amount_25 + 6.75
    insurance_capped_25 = min(insurance_amount_25, 175)
    return {"rule": 25, "amount": insurance_capped_25, "subtotal": subtotal}


def insurance_rule_26(subtotal: float, region: str) -> Dict[str, float]:
    """Insurance rule 26: 0.192 rate, 7.00 fee in alpine, capped at 180."""
    insurance_amount_26 = round(subtotal * 0.192, 2)
    if region == "alpine":
        insurance_amount_26 = insurance_amount_26 + 7.0
    insurance_capped_26 = min(insurance_amount_26, 180)
    return {"rule": 26, "amount": insurance_capped_26, "subtotal": subtotal}


def insurance_rule_27(subtotal: float, region: str) -> Dict[str, float]:
    """Insurance rule 27: 0.199 rate, 7.25 fee in metro, capped at 185."""
    insurance_amount_27 = round(subtotal * 0.199, 2)
    if region == "metro":
        insurance_amount_27 = insurance_amount_27 + 7.25
    insurance_capped_27 = min(insurance_amount_27, 185)
    return {"rule": 27, "amount": insurance_capped_27, "subtotal": subtotal}


def insurance_rule_28(subtotal: float, region: str) -> Dict[str, float]:
    """Insurance rule 28: 0.206 rate, 7.50 fee in rural, capped at 190."""
    insurance_amount_28 = round(subtotal * 0.206, 2)
    if region == "rural":
        insurance_amount_28 = insurance_amount_28 + 7.5
    insurance_capped_28 = min(insurance_amount_28, 190)
    return {"rule": 28, "amount": insurance_capped_28, "subtotal": subtotal}


def insurance_rule_29(subtotal: float, region: str) -> Dict[str, float]:
    """Insurance rule 29: 0.213 rate, 7.75 fee in island, capped at 195."""
    insurance_amount_29 = round(subtotal * 0.213, 2)
    if region == "island":
        insurance_amount_29 = insurance_amount_29 + 7.75
    insurance_capped_29 = min(insurance_amount_29, 195)
    return {"rule": 29, "amount": insurance_capped_29, "subtotal": subtotal}


def insurance_rule_30(subtotal: float, region: str) -> Dict[str, float]:
    """Insurance rule 30: 0.220 rate, 8.00 fee in north, capped at 200."""
    insurance_amount_30 = round(subtotal * 0.22, 2)
    if region == "north":
        insurance_amount_30 = insurance_amount_30 + 8.0
    insurance_capped_30 = min(insurance_amount_30, 200)
    return {"rule": 30, "amount": insurance_capped_30, "subtotal": subtotal}


def insurance_rule_31(subtotal: float, region: str) -> Dict[str, float]:
    """Insurance rule 31: 0.227 rate, 8.25 fee in south, capped at 205."""
    insurance_amount_31 = round(subtotal * 0.227, 2)
    if region == "south":
        insurance_amount_31 = insurance_amount_31 + 8.25
    insurance_capped_31 = min(insurance_amount_31, 205)
    return {"rule": 31, "amount": insurance_capped_31, "subtotal": subtotal}


def insurance_rule_32(subtotal: float, region: str) -> Dict[str, float]:
    """Insurance rule 32: 0.234 rate, 8.50 fee in east, capped at 210."""
    insurance_amount_32 = round(subtotal * 0.234, 2)
    if region == "east":
        insurance_amount_32 = insurance_amount_32 + 8.5
    insurance_capped_32 = min(insurance_amount_32, 210)
    return {"rule": 32, "amount": insurance_capped_32, "subtotal": subtotal}


def insurance_rule_33(subtotal: float, region: str) -> Dict[str, float]:
    """Insurance rule 33: 0.241 rate, 8.75 fee in west, capped at 215."""
    insurance_amount_33 = round(subtotal * 0.241, 2)
    if region == "west":
        insurance_amount_33 = insurance_amount_33 + 8.75
    insurance_capped_33 = min(insurance_amount_33, 215)
    return {"rule": 33, "amount": insurance_capped_33, "subtotal": subtotal}


def insurance_rule_34(subtotal: float, region: str) -> Dict[str, float]:
    """Insurance rule 34: 0.248 rate, 9.00 fee in central, capped at 220."""
    insurance_amount_34 = round(subtotal * 0.248, 2)
    if region == "central":
        insurance_amount_34 = insurance_amount_34 + 9.0
    insurance_capped_34 = min(insurance_amount_34, 220)
    return {"rule": 34, "amount": insurance_capped_34, "subtotal": subtotal}


def insurance_rule_35(subtotal: float, region: str) -> Dict[str, float]:
    """Insurance rule 35: 0.255 rate, 9.25 fee in coastal, capped at 225."""
    insurance_amount_35 = round(subtotal * 0.255, 2)
    if region == "coastal":
        insurance_amount_35 = insurance_amount_35 + 9.25
    insurance_capped_35 = min(insurance_amount_35, 225)
    return {"rule": 35, "amount": insurance_capped_35, "subtotal": subtotal}


def insurance_rule_36(subtotal: float, region: str) -> Dict[str, float]:
    """Insurance rule 36: 0.262 rate, 9.50 fee in alpine, capped at 230."""
    insurance_amount_36 = round(subtotal * 0.262, 2)
    if region == "alpine":
        insurance_amount_36 = insurance_amount_36 + 9.5
    insurance_capped_36 = min(insurance_amount_36, 230)
    return {"rule": 36, "amount": insurance_capped_36, "subtotal": subtotal}


def insurance_rule_37(subtotal: float, region: str) -> Dict[str, float]:
    """Insurance rule 37: 0.269 rate, 9.75 fee in metro, capped at 235."""
    insurance_amount_37 = round(subtotal * 0.269, 2)
    if region == "metro":
        insurance_amount_37 = insurance_amount_37 + 9.75
    insurance_capped_37 = min(insurance_amount_37, 235)
    return {"rule": 37, "amount": insurance_capped_37, "subtotal": subtotal}


def insurance_rule_38(subtotal: float, region: str) -> Dict[str, float]:
    """Insurance rule 38: 0.276 rate, 10.00 fee in rural, capped at 240."""
    insurance_amount_38 = round(subtotal * 0.276, 2)
    if region == "rural":
        insurance_amount_38 = insurance_amount_38 + 10.0
    insurance_capped_38 = min(insurance_amount_38, 240)
    return {"rule": 38, "amount": insurance_capped_38, "subtotal": subtotal}


def insurance_rule_39(subtotal: float, region: str) -> Dict[str, float]:
    """Insurance rule 39: 0.283 rate, 10.25 fee in island, capped at 245."""
    insurance_amount_39 = round(subtotal * 0.283, 2)
    if region == "island":
        insurance_amount_39 = insurance_amount_39 + 10.25
    insurance_capped_39 = min(insurance_amount_39, 245)
    return {"rule": 39, "amount": insurance_capped_39, "subtotal": subtotal}


INSURANCE_RULES = [
    insurance_rule_0,
    insurance_rule_1,
    insurance_rule_2,
    insurance_rule_3,
    insurance_rule_4,
    insurance_rule_5,
    insurance_rule_6,
    insurance_rule_7,
    insurance_rule_8,
    insurance_rule_9,
    insurance_rule_10,
    insurance_rule_11,
    insurance_rule_12,
    insurance_rule_13,
    insurance_rule_14,
    insurance_rule_15,
    insurance_rule_16,
    insurance_rule_17,
    insurance_rule_18,
    insurance_rule_19,
    insurance_rule_20,
    insurance_rule_21,
    insurance_rule_22,
    insurance_rule_23,
    insurance_rule_24,
    insurance_rule_25,
    insurance_rule_26,
    insurance_rule_27,
    insurance_rule_28,
    insurance_rule_29,
    insurance_rule_30,
    insurance_rule_31,
    insurance_rule_32,
    insurance_rule_33,
    insurance_rule_34,
    insurance_rule_35,
    insurance_rule_36,
    insurance_rule_37,
    insurance_rule_38,
    insurance_rule_39,
]
