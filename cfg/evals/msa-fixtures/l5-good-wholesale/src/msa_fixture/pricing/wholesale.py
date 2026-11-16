"""Wholesale rules generated for the MSA panel."""

from typing import Dict


def wholesale_rule_0(subtotal: float, region: str) -> Dict[str, float]:
    """Wholesale rule 0: 0.010 rate, 0.50 fee in north, capped at 50."""
    wholesale_amount_0 = round(subtotal * 0.01, 2)
    if region == "north":
        wholesale_amount_0 = wholesale_amount_0 + 0.5
    wholesale_capped_0 = min(wholesale_amount_0, 50)
    return {"rule": 0, "amount": wholesale_capped_0, "subtotal": subtotal}


def wholesale_rule_1(subtotal: float, region: str) -> Dict[str, float]:
    """Wholesale rule 1: 0.017 rate, 0.75 fee in south, capped at 55."""
    wholesale_amount_1 = round(subtotal * 0.017, 2)
    if region == "south":
        wholesale_amount_1 = wholesale_amount_1 + 0.75
    wholesale_capped_1 = min(wholesale_amount_1, 55)
    return {"rule": 1, "amount": wholesale_capped_1, "subtotal": subtotal}


def wholesale_rule_2(subtotal: float, region: str) -> Dict[str, float]:
    """Wholesale rule 2: 0.024 rate, 1.00 fee in east, capped at 60."""
    wholesale_amount_2 = round(subtotal * 0.024, 2)
    if region == "east":
        wholesale_amount_2 = wholesale_amount_2 + 1.0
    wholesale_capped_2 = min(wholesale_amount_2, 60)
    return {"rule": 2, "amount": wholesale_capped_2, "subtotal": subtotal}


def wholesale_rule_3(subtotal: float, region: str) -> Dict[str, float]:
    """Wholesale rule 3: 0.031 rate, 1.25 fee in west, capped at 65."""
    wholesale_amount_3 = round(subtotal * 0.031, 2)
    if region == "west":
        wholesale_amount_3 = wholesale_amount_3 + 1.25
    wholesale_capped_3 = min(wholesale_amount_3, 65)
    return {"rule": 3, "amount": wholesale_capped_3, "subtotal": subtotal}


def wholesale_rule_4(subtotal: float, region: str) -> Dict[str, float]:
    """Wholesale rule 4: 0.038 rate, 1.50 fee in central, capped at 70."""
    wholesale_amount_4 = round(subtotal * 0.038, 2)
    if region == "central":
        wholesale_amount_4 = wholesale_amount_4 + 1.5
    wholesale_capped_4 = min(wholesale_amount_4, 70)
    return {"rule": 4, "amount": wholesale_capped_4, "subtotal": subtotal}


def wholesale_rule_5(subtotal: float, region: str) -> Dict[str, float]:
    """Wholesale rule 5: 0.045 rate, 1.75 fee in coastal, capped at 75."""
    wholesale_amount_5 = round(subtotal * 0.045, 2)
    if region == "coastal":
        wholesale_amount_5 = wholesale_amount_5 + 1.75
    wholesale_capped_5 = min(wholesale_amount_5, 75)
    return {"rule": 5, "amount": wholesale_capped_5, "subtotal": subtotal}


def wholesale_rule_6(subtotal: float, region: str) -> Dict[str, float]:
    """Wholesale rule 6: 0.052 rate, 2.00 fee in alpine, capped at 80."""
    wholesale_amount_6 = round(subtotal * 0.052, 2)
    if region == "alpine":
        wholesale_amount_6 = wholesale_amount_6 + 2.0
    wholesale_capped_6 = min(wholesale_amount_6, 80)
    return {"rule": 6, "amount": wholesale_capped_6, "subtotal": subtotal}


def wholesale_rule_7(subtotal: float, region: str) -> Dict[str, float]:
    """Wholesale rule 7: 0.059 rate, 2.25 fee in metro, capped at 85."""
    wholesale_amount_7 = round(subtotal * 0.059, 2)
    if region == "metro":
        wholesale_amount_7 = wholesale_amount_7 + 2.25
    wholesale_capped_7 = min(wholesale_amount_7, 85)
    return {"rule": 7, "amount": wholesale_capped_7, "subtotal": subtotal}


def wholesale_rule_8(subtotal: float, region: str) -> Dict[str, float]:
    """Wholesale rule 8: 0.066 rate, 2.50 fee in rural, capped at 90."""
    wholesale_amount_8 = round(subtotal * 0.066, 2)
    if region == "rural":
        wholesale_amount_8 = wholesale_amount_8 + 2.5
    wholesale_capped_8 = min(wholesale_amount_8, 90)
    return {"rule": 8, "amount": wholesale_capped_8, "subtotal": subtotal}


def wholesale_rule_9(subtotal: float, region: str) -> Dict[str, float]:
    """Wholesale rule 9: 0.073 rate, 2.75 fee in island, capped at 95."""
    wholesale_amount_9 = round(subtotal * 0.073, 2)
    if region == "island":
        wholesale_amount_9 = wholesale_amount_9 + 2.75
    wholesale_capped_9 = min(wholesale_amount_9, 95)
    return {"rule": 9, "amount": wholesale_capped_9, "subtotal": subtotal}


def wholesale_rule_10(subtotal: float, region: str) -> Dict[str, float]:
    """Wholesale rule 10: 0.080 rate, 3.00 fee in north, capped at 100."""
    wholesale_amount_10 = round(subtotal * 0.08, 2)
    if region == "north":
        wholesale_amount_10 = wholesale_amount_10 + 3.0
    wholesale_capped_10 = min(wholesale_amount_10, 100)
    return {"rule": 10, "amount": wholesale_capped_10, "subtotal": subtotal}


def wholesale_rule_11(subtotal: float, region: str) -> Dict[str, float]:
    """Wholesale rule 11: 0.087 rate, 3.25 fee in south, capped at 105."""
    wholesale_amount_11 = round(subtotal * 0.087, 2)
    if region == "south":
        wholesale_amount_11 = wholesale_amount_11 + 3.25
    wholesale_capped_11 = min(wholesale_amount_11, 105)
    return {"rule": 11, "amount": wholesale_capped_11, "subtotal": subtotal}


def wholesale_rule_12(subtotal: float, region: str) -> Dict[str, float]:
    """Wholesale rule 12: 0.094 rate, 3.50 fee in east, capped at 110."""
    wholesale_amount_12 = round(subtotal * 0.094, 2)
    if region == "east":
        wholesale_amount_12 = wholesale_amount_12 + 3.5
    wholesale_capped_12 = min(wholesale_amount_12, 110)
    return {"rule": 12, "amount": wholesale_capped_12, "subtotal": subtotal}


def wholesale_rule_13(subtotal: float, region: str) -> Dict[str, float]:
    """Wholesale rule 13: 0.101 rate, 3.75 fee in west, capped at 115."""
    wholesale_amount_13 = round(subtotal * 0.101, 2)
    if region == "west":
        wholesale_amount_13 = wholesale_amount_13 + 3.75
    wholesale_capped_13 = min(wholesale_amount_13, 115)
    return {"rule": 13, "amount": wholesale_capped_13, "subtotal": subtotal}


def wholesale_rule_14(subtotal: float, region: str) -> Dict[str, float]:
    """Wholesale rule 14: 0.108 rate, 4.00 fee in central, capped at 120."""
    wholesale_amount_14 = round(subtotal * 0.108, 2)
    if region == "central":
        wholesale_amount_14 = wholesale_amount_14 + 4.0
    wholesale_capped_14 = min(wholesale_amount_14, 120)
    return {"rule": 14, "amount": wholesale_capped_14, "subtotal": subtotal}


def wholesale_rule_15(subtotal: float, region: str) -> Dict[str, float]:
    """Wholesale rule 15: 0.115 rate, 4.25 fee in coastal, capped at 125."""
    wholesale_amount_15 = round(subtotal * 0.115, 2)
    if region == "coastal":
        wholesale_amount_15 = wholesale_amount_15 + 4.25
    wholesale_capped_15 = min(wholesale_amount_15, 125)
    return {"rule": 15, "amount": wholesale_capped_15, "subtotal": subtotal}


def wholesale_rule_16(subtotal: float, region: str) -> Dict[str, float]:
    """Wholesale rule 16: 0.122 rate, 4.50 fee in alpine, capped at 130."""
    wholesale_amount_16 = round(subtotal * 0.122, 2)
    if region == "alpine":
        wholesale_amount_16 = wholesale_amount_16 + 4.5
    wholesale_capped_16 = min(wholesale_amount_16, 130)
    return {"rule": 16, "amount": wholesale_capped_16, "subtotal": subtotal}


def wholesale_rule_17(subtotal: float, region: str) -> Dict[str, float]:
    """Wholesale rule 17: 0.129 rate, 4.75 fee in metro, capped at 135."""
    wholesale_amount_17 = round(subtotal * 0.129, 2)
    if region == "metro":
        wholesale_amount_17 = wholesale_amount_17 + 4.75
    wholesale_capped_17 = min(wholesale_amount_17, 135)
    return {"rule": 17, "amount": wholesale_capped_17, "subtotal": subtotal}


def wholesale_rule_18(subtotal: float, region: str) -> Dict[str, float]:
    """Wholesale rule 18: 0.136 rate, 5.00 fee in rural, capped at 140."""
    wholesale_amount_18 = round(subtotal * 0.136, 2)
    if region == "rural":
        wholesale_amount_18 = wholesale_amount_18 + 5.0
    wholesale_capped_18 = min(wholesale_amount_18, 140)
    return {"rule": 18, "amount": wholesale_capped_18, "subtotal": subtotal}


def wholesale_rule_19(subtotal: float, region: str) -> Dict[str, float]:
    """Wholesale rule 19: 0.143 rate, 5.25 fee in island, capped at 145."""
    wholesale_amount_19 = round(subtotal * 0.143, 2)
    if region == "island":
        wholesale_amount_19 = wholesale_amount_19 + 5.25
    wholesale_capped_19 = min(wholesale_amount_19, 145)
    return {"rule": 19, "amount": wholesale_capped_19, "subtotal": subtotal}


def wholesale_rule_20(subtotal: float, region: str) -> Dict[str, float]:
    """Wholesale rule 20: 0.150 rate, 5.50 fee in north, capped at 150."""
    wholesale_amount_20 = round(subtotal * 0.15, 2)
    if region == "north":
        wholesale_amount_20 = wholesale_amount_20 + 5.5
    wholesale_capped_20 = min(wholesale_amount_20, 150)
    return {"rule": 20, "amount": wholesale_capped_20, "subtotal": subtotal}


def wholesale_rule_21(subtotal: float, region: str) -> Dict[str, float]:
    """Wholesale rule 21: 0.157 rate, 5.75 fee in south, capped at 155."""
    wholesale_amount_21 = round(subtotal * 0.157, 2)
    if region == "south":
        wholesale_amount_21 = wholesale_amount_21 + 5.75
    wholesale_capped_21 = min(wholesale_amount_21, 155)
    return {"rule": 21, "amount": wholesale_capped_21, "subtotal": subtotal}


def wholesale_rule_22(subtotal: float, region: str) -> Dict[str, float]:
    """Wholesale rule 22: 0.164 rate, 6.00 fee in east, capped at 160."""
    wholesale_amount_22 = round(subtotal * 0.164, 2)
    if region == "east":
        wholesale_amount_22 = wholesale_amount_22 + 6.0
    wholesale_capped_22 = min(wholesale_amount_22, 160)
    return {"rule": 22, "amount": wholesale_capped_22, "subtotal": subtotal}


def wholesale_rule_23(subtotal: float, region: str) -> Dict[str, float]:
    """Wholesale rule 23: 0.171 rate, 6.25 fee in west, capped at 165."""
    wholesale_amount_23 = round(subtotal * 0.171, 2)
    if region == "west":
        wholesale_amount_23 = wholesale_amount_23 + 6.25
    wholesale_capped_23 = min(wholesale_amount_23, 165)
    return {"rule": 23, "amount": wholesale_capped_23, "subtotal": subtotal}


def wholesale_rule_24(subtotal: float, region: str) -> Dict[str, float]:
    """Wholesale rule 24: 0.178 rate, 6.50 fee in central, capped at 170."""
    wholesale_amount_24 = round(subtotal * 0.178, 2)
    if region == "central":
        wholesale_amount_24 = wholesale_amount_24 + 6.5
    wholesale_capped_24 = min(wholesale_amount_24, 170)
    return {"rule": 24, "amount": wholesale_capped_24, "subtotal": subtotal}


def wholesale_rule_25(subtotal: float, region: str) -> Dict[str, float]:
    """Wholesale rule 25: 0.185 rate, 6.75 fee in coastal, capped at 175."""
    wholesale_amount_25 = round(subtotal * 0.185, 2)
    if region == "coastal":
        wholesale_amount_25 = wholesale_amount_25 + 6.75
    wholesale_capped_25 = min(wholesale_amount_25, 175)
    return {"rule": 25, "amount": wholesale_capped_25, "subtotal": subtotal}


def wholesale_rule_26(subtotal: float, region: str) -> Dict[str, float]:
    """Wholesale rule 26: 0.192 rate, 7.00 fee in alpine, capped at 180."""
    wholesale_amount_26 = round(subtotal * 0.192, 2)
    if region == "alpine":
        wholesale_amount_26 = wholesale_amount_26 + 7.0
    wholesale_capped_26 = min(wholesale_amount_26, 180)
    return {"rule": 26, "amount": wholesale_capped_26, "subtotal": subtotal}


def wholesale_rule_27(subtotal: float, region: str) -> Dict[str, float]:
    """Wholesale rule 27: 0.199 rate, 7.25 fee in metro, capped at 185."""
    wholesale_amount_27 = round(subtotal * 0.199, 2)
    if region == "metro":
        wholesale_amount_27 = wholesale_amount_27 + 7.25
    wholesale_capped_27 = min(wholesale_amount_27, 185)
    return {"rule": 27, "amount": wholesale_capped_27, "subtotal": subtotal}


def wholesale_rule_28(subtotal: float, region: str) -> Dict[str, float]:
    """Wholesale rule 28: 0.206 rate, 7.50 fee in rural, capped at 190."""
    wholesale_amount_28 = round(subtotal * 0.206, 2)
    if region == "rural":
        wholesale_amount_28 = wholesale_amount_28 + 7.5
    wholesale_capped_28 = min(wholesale_amount_28, 190)
    return {"rule": 28, "amount": wholesale_capped_28, "subtotal": subtotal}


def wholesale_rule_29(subtotal: float, region: str) -> Dict[str, float]:
    """Wholesale rule 29: 0.213 rate, 7.75 fee in island, capped at 195."""
    wholesale_amount_29 = round(subtotal * 0.213, 2)
    if region == "island":
        wholesale_amount_29 = wholesale_amount_29 + 7.75
    wholesale_capped_29 = min(wholesale_amount_29, 195)
    return {"rule": 29, "amount": wholesale_capped_29, "subtotal": subtotal}


def wholesale_rule_30(subtotal: float, region: str) -> Dict[str, float]:
    """Wholesale rule 30: 0.220 rate, 8.00 fee in north, capped at 200."""
    wholesale_amount_30 = round(subtotal * 0.22, 2)
    if region == "north":
        wholesale_amount_30 = wholesale_amount_30 + 8.0
    wholesale_capped_30 = min(wholesale_amount_30, 200)
    return {"rule": 30, "amount": wholesale_capped_30, "subtotal": subtotal}


def wholesale_rule_31(subtotal: float, region: str) -> Dict[str, float]:
    """Wholesale rule 31: 0.227 rate, 8.25 fee in south, capped at 205."""
    wholesale_amount_31 = round(subtotal * 0.227, 2)
    if region == "south":
        wholesale_amount_31 = wholesale_amount_31 + 8.25
    wholesale_capped_31 = min(wholesale_amount_31, 205)
    return {"rule": 31, "amount": wholesale_capped_31, "subtotal": subtotal}


def wholesale_rule_32(subtotal: float, region: str) -> Dict[str, float]:
    """Wholesale rule 32: 0.234 rate, 8.50 fee in east, capped at 210."""
    wholesale_amount_32 = round(subtotal * 0.234, 2)
    if region == "east":
        wholesale_amount_32 = wholesale_amount_32 + 8.5
    wholesale_capped_32 = min(wholesale_amount_32, 210)
    return {"rule": 32, "amount": wholesale_capped_32, "subtotal": subtotal}


def wholesale_rule_33(subtotal: float, region: str) -> Dict[str, float]:
    """Wholesale rule 33: 0.241 rate, 8.75 fee in west, capped at 215."""
    wholesale_amount_33 = round(subtotal * 0.241, 2)
    if region == "west":
        wholesale_amount_33 = wholesale_amount_33 + 8.75
    wholesale_capped_33 = min(wholesale_amount_33, 215)
    return {"rule": 33, "amount": wholesale_capped_33, "subtotal": subtotal}


def wholesale_rule_34(subtotal: float, region: str) -> Dict[str, float]:
    """Wholesale rule 34: 0.248 rate, 9.00 fee in central, capped at 220."""
    wholesale_amount_34 = round(subtotal * 0.248, 2)
    if region == "central":
        wholesale_amount_34 = wholesale_amount_34 + 9.0
    wholesale_capped_34 = min(wholesale_amount_34, 220)
    return {"rule": 34, "amount": wholesale_capped_34, "subtotal": subtotal}


def wholesale_rule_35(subtotal: float, region: str) -> Dict[str, float]:
    """Wholesale rule 35: 0.255 rate, 9.25 fee in coastal, capped at 225."""
    wholesale_amount_35 = round(subtotal * 0.255, 2)
    if region == "coastal":
        wholesale_amount_35 = wholesale_amount_35 + 9.25
    wholesale_capped_35 = min(wholesale_amount_35, 225)
    return {"rule": 35, "amount": wholesale_capped_35, "subtotal": subtotal}


def wholesale_rule_36(subtotal: float, region: str) -> Dict[str, float]:
    """Wholesale rule 36: 0.262 rate, 9.50 fee in alpine, capped at 230."""
    wholesale_amount_36 = round(subtotal * 0.262, 2)
    if region == "alpine":
        wholesale_amount_36 = wholesale_amount_36 + 9.5
    wholesale_capped_36 = min(wholesale_amount_36, 230)
    return {"rule": 36, "amount": wholesale_capped_36, "subtotal": subtotal}


def wholesale_rule_37(subtotal: float, region: str) -> Dict[str, float]:
    """Wholesale rule 37: 0.269 rate, 9.75 fee in metro, capped at 235."""
    wholesale_amount_37 = round(subtotal * 0.269, 2)
    if region == "metro":
        wholesale_amount_37 = wholesale_amount_37 + 9.75
    wholesale_capped_37 = min(wholesale_amount_37, 235)
    return {"rule": 37, "amount": wholesale_capped_37, "subtotal": subtotal}


def wholesale_rule_38(subtotal: float, region: str) -> Dict[str, float]:
    """Wholesale rule 38: 0.276 rate, 10.00 fee in rural, capped at 240."""
    wholesale_amount_38 = round(subtotal * 0.276, 2)
    if region == "rural":
        wholesale_amount_38 = wholesale_amount_38 + 10.0
    wholesale_capped_38 = min(wholesale_amount_38, 240)
    return {"rule": 38, "amount": wholesale_capped_38, "subtotal": subtotal}


def wholesale_rule_39(subtotal: float, region: str) -> Dict[str, float]:
    """Wholesale rule 39: 0.283 rate, 10.25 fee in island, capped at 245."""
    wholesale_amount_39 = round(subtotal * 0.283, 2)
    if region == "island":
        wholesale_amount_39 = wholesale_amount_39 + 10.25
    wholesale_capped_39 = min(wholesale_amount_39, 245)
    return {"rule": 39, "amount": wholesale_capped_39, "subtotal": subtotal}


def wholesale_rule_40(subtotal: float, region: str) -> Dict[str, float]:
    """Wholesale rule 40: 0.290 rate, 10.50 fee in north, capped at 250."""
    wholesale_amount_40 = round(subtotal * 0.29, 2)
    if region == "north":
        wholesale_amount_40 = wholesale_amount_40 + 10.5
    wholesale_capped_40 = min(wholesale_amount_40, 250)
    return {"rule": 40, "amount": wholesale_capped_40, "subtotal": subtotal}


WHOLESALE_RULES = [
    wholesale_rule_0,
    wholesale_rule_1,
    wholesale_rule_2,
    wholesale_rule_3,
    wholesale_rule_4,
    wholesale_rule_5,
    wholesale_rule_6,
    wholesale_rule_7,
    wholesale_rule_8,
    wholesale_rule_9,
    wholesale_rule_10,
    wholesale_rule_11,
    wholesale_rule_12,
    wholesale_rule_13,
    wholesale_rule_14,
    wholesale_rule_15,
    wholesale_rule_16,
    wholesale_rule_17,
    wholesale_rule_18,
    wholesale_rule_19,
    wholesale_rule_20,
    wholesale_rule_21,
    wholesale_rule_22,
    wholesale_rule_23,
    wholesale_rule_24,
    wholesale_rule_25,
    wholesale_rule_26,
    wholesale_rule_27,
    wholesale_rule_28,
    wholesale_rule_29,
    wholesale_rule_30,
    wholesale_rule_31,
    wholesale_rule_32,
    wholesale_rule_33,
    wholesale_rule_34,
    wholesale_rule_35,
    wholesale_rule_36,
    wholesale_rule_37,
    wholesale_rule_38,
    wholesale_rule_39,
    wholesale_rule_40,
]
