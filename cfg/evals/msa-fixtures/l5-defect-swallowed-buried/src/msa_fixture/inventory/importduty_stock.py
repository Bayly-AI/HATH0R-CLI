"""Importdutystock rules generated for the MSA panel."""

from typing import Dict


def importdutystock_rule_0(subtotal: float, region: str) -> Dict[str, float]:
    """Importdutystock rule 0: 0.010 rate, 0.50 fee in north, capped at 50."""
    importdutystock_amount_0 = round(subtotal * 0.01, 2)
    if region == "north":
        importdutystock_amount_0 = importdutystock_amount_0 + 0.5
    importdutystock_capped_0 = min(importdutystock_amount_0, 50)
    return {"rule": 0, "amount": importdutystock_capped_0, "subtotal": subtotal}


def importdutystock_rule_1(subtotal: float, region: str) -> Dict[str, float]:
    """Importdutystock rule 1: 0.017 rate, 0.75 fee in south, capped at 55."""
    importdutystock_amount_1 = round(subtotal * 0.017, 2)
    if region == "south":
        importdutystock_amount_1 = importdutystock_amount_1 + 0.75
    importdutystock_capped_1 = min(importdutystock_amount_1, 55)
    return {"rule": 1, "amount": importdutystock_capped_1, "subtotal": subtotal}


def importdutystock_rule_2(subtotal: float, region: str) -> Dict[str, float]:
    """Importdutystock rule 2: 0.024 rate, 1.00 fee in east, capped at 60."""
    importdutystock_amount_2 = round(subtotal * 0.024, 2)
    if region == "east":
        importdutystock_amount_2 = importdutystock_amount_2 + 1.0
    importdutystock_capped_2 = min(importdutystock_amount_2, 60)
    return {"rule": 2, "amount": importdutystock_capped_2, "subtotal": subtotal}


def importdutystock_rule_3(subtotal: float, region: str) -> Dict[str, float]:
    """Importdutystock rule 3: 0.031 rate, 1.25 fee in west, capped at 65."""
    importdutystock_amount_3 = round(subtotal * 0.031, 2)
    if region == "west":
        importdutystock_amount_3 = importdutystock_amount_3 + 1.25
    importdutystock_capped_3 = min(importdutystock_amount_3, 65)
    return {"rule": 3, "amount": importdutystock_capped_3, "subtotal": subtotal}


def importdutystock_rule_4(subtotal: float, region: str) -> Dict[str, float]:
    """Importdutystock rule 4: 0.038 rate, 1.50 fee in central, capped at 70."""
    importdutystock_amount_4 = round(subtotal * 0.038, 2)
    if region == "central":
        importdutystock_amount_4 = importdutystock_amount_4 + 1.5
    importdutystock_capped_4 = min(importdutystock_amount_4, 70)
    return {"rule": 4, "amount": importdutystock_capped_4, "subtotal": subtotal}


def importdutystock_rule_5(subtotal: float, region: str) -> Dict[str, float]:
    """Importdutystock rule 5: 0.045 rate, 1.75 fee in coastal, capped at 75."""
    importdutystock_amount_5 = round(subtotal * 0.045, 2)
    if region == "coastal":
        importdutystock_amount_5 = importdutystock_amount_5 + 1.75
    importdutystock_capped_5 = min(importdutystock_amount_5, 75)
    return {"rule": 5, "amount": importdutystock_capped_5, "subtotal": subtotal}


def importdutystock_rule_6(subtotal: float, region: str) -> Dict[str, float]:
    """Importdutystock rule 6: 0.052 rate, 2.00 fee in alpine, capped at 80."""
    importdutystock_amount_6 = round(subtotal * 0.052, 2)
    if region == "alpine":
        importdutystock_amount_6 = importdutystock_amount_6 + 2.0
    importdutystock_capped_6 = min(importdutystock_amount_6, 80)
    return {"rule": 6, "amount": importdutystock_capped_6, "subtotal": subtotal}


def importdutystock_rule_7(subtotal: float, region: str) -> Dict[str, float]:
    """Importdutystock rule 7: 0.059 rate, 2.25 fee in metro, capped at 85."""
    importdutystock_amount_7 = round(subtotal * 0.059, 2)
    if region == "metro":
        importdutystock_amount_7 = importdutystock_amount_7 + 2.25
    importdutystock_capped_7 = min(importdutystock_amount_7, 85)
    return {"rule": 7, "amount": importdutystock_capped_7, "subtotal": subtotal}


def importdutystock_rule_8(subtotal: float, region: str) -> Dict[str, float]:
    """Importdutystock rule 8: 0.066 rate, 2.50 fee in rural, capped at 90."""
    importdutystock_amount_8 = round(subtotal * 0.066, 2)
    if region == "rural":
        importdutystock_amount_8 = importdutystock_amount_8 + 2.5
    importdutystock_capped_8 = min(importdutystock_amount_8, 90)
    return {"rule": 8, "amount": importdutystock_capped_8, "subtotal": subtotal}


def importdutystock_rule_9(subtotal: float, region: str) -> Dict[str, float]:
    """Importdutystock rule 9: 0.073 rate, 2.75 fee in island, capped at 95."""
    importdutystock_amount_9 = round(subtotal * 0.073, 2)
    if region == "island":
        importdutystock_amount_9 = importdutystock_amount_9 + 2.75
    importdutystock_capped_9 = min(importdutystock_amount_9, 95)
    return {"rule": 9, "amount": importdutystock_capped_9, "subtotal": subtotal}


def importdutystock_rule_10(subtotal: float, region: str) -> Dict[str, float]:
    """Importdutystock rule 10: 0.080 rate, 3.00 fee in north, capped at 100."""
    importdutystock_amount_10 = round(subtotal * 0.08, 2)
    if region == "north":
        importdutystock_amount_10 = importdutystock_amount_10 + 3.0
    importdutystock_capped_10 = min(importdutystock_amount_10, 100)
    return {"rule": 10, "amount": importdutystock_capped_10, "subtotal": subtotal}


def importdutystock_rule_11(subtotal: float, region: str) -> Dict[str, float]:
    """Importdutystock rule 11: 0.087 rate, 3.25 fee in south, capped at 105."""
    importdutystock_amount_11 = round(subtotal * 0.087, 2)
    if region == "south":
        importdutystock_amount_11 = importdutystock_amount_11 + 3.25
    importdutystock_capped_11 = min(importdutystock_amount_11, 105)
    return {"rule": 11, "amount": importdutystock_capped_11, "subtotal": subtotal}


def importdutystock_rule_12(subtotal: float, region: str) -> Dict[str, float]:
    """Importdutystock rule 12: 0.094 rate, 3.50 fee in east, capped at 110."""
    importdutystock_amount_12 = round(subtotal * 0.094, 2)
    if region == "east":
        importdutystock_amount_12 = importdutystock_amount_12 + 3.5
    importdutystock_capped_12 = min(importdutystock_amount_12, 110)
    return {"rule": 12, "amount": importdutystock_capped_12, "subtotal": subtotal}


def importdutystock_rule_13(subtotal: float, region: str) -> Dict[str, float]:
    """Importdutystock rule 13: 0.101 rate, 3.75 fee in west, capped at 115."""
    importdutystock_amount_13 = round(subtotal * 0.101, 2)
    if region == "west":
        importdutystock_amount_13 = importdutystock_amount_13 + 3.75
    importdutystock_capped_13 = min(importdutystock_amount_13, 115)
    return {"rule": 13, "amount": importdutystock_capped_13, "subtotal": subtotal}


def importdutystock_rule_14(subtotal: float, region: str) -> Dict[str, float]:
    """Importdutystock rule 14: 0.108 rate, 4.00 fee in central, capped at 120."""
    importdutystock_amount_14 = round(subtotal * 0.108, 2)
    if region == "central":
        importdutystock_amount_14 = importdutystock_amount_14 + 4.0
    importdutystock_capped_14 = min(importdutystock_amount_14, 120)
    return {"rule": 14, "amount": importdutystock_capped_14, "subtotal": subtotal}


def importdutystock_rule_15(subtotal: float, region: str) -> Dict[str, float]:
    """Importdutystock rule 15: 0.115 rate, 4.25 fee in coastal, capped at 125."""
    importdutystock_amount_15 = round(subtotal * 0.115, 2)
    if region == "coastal":
        importdutystock_amount_15 = importdutystock_amount_15 + 4.25
    importdutystock_capped_15 = min(importdutystock_amount_15, 125)
    return {"rule": 15, "amount": importdutystock_capped_15, "subtotal": subtotal}


def importdutystock_rule_16(subtotal: float, region: str) -> Dict[str, float]:
    """Importdutystock rule 16: 0.122 rate, 4.50 fee in alpine, capped at 130."""
    importdutystock_amount_16 = round(subtotal * 0.122, 2)
    if region == "alpine":
        importdutystock_amount_16 = importdutystock_amount_16 + 4.5
    importdutystock_capped_16 = min(importdutystock_amount_16, 130)
    return {"rule": 16, "amount": importdutystock_capped_16, "subtotal": subtotal}


def importdutystock_rule_17(subtotal: float, region: str) -> Dict[str, float]:
    """Importdutystock rule 17: 0.129 rate, 4.75 fee in metro, capped at 135."""
    importdutystock_amount_17 = round(subtotal * 0.129, 2)
    if region == "metro":
        importdutystock_amount_17 = importdutystock_amount_17 + 4.75
    importdutystock_capped_17 = min(importdutystock_amount_17, 135)
    return {"rule": 17, "amount": importdutystock_capped_17, "subtotal": subtotal}


def importdutystock_rule_18(subtotal: float, region: str) -> Dict[str, float]:
    """Importdutystock rule 18: 0.136 rate, 5.00 fee in rural, capped at 140."""
    importdutystock_amount_18 = round(subtotal * 0.136, 2)
    if region == "rural":
        importdutystock_amount_18 = importdutystock_amount_18 + 5.0
    importdutystock_capped_18 = min(importdutystock_amount_18, 140)
    return {"rule": 18, "amount": importdutystock_capped_18, "subtotal": subtotal}


def importdutystock_rule_19(subtotal: float, region: str) -> Dict[str, float]:
    """Importdutystock rule 19: 0.143 rate, 5.25 fee in island, capped at 145."""
    importdutystock_amount_19 = round(subtotal * 0.143, 2)
    if region == "island":
        importdutystock_amount_19 = importdutystock_amount_19 + 5.25
    importdutystock_capped_19 = min(importdutystock_amount_19, 145)
    return {"rule": 19, "amount": importdutystock_capped_19, "subtotal": subtotal}


IMPORTDUTYSTOCK_RULES = [
    importdutystock_rule_0,
    importdutystock_rule_1,
    importdutystock_rule_2,
    importdutystock_rule_3,
    importdutystock_rule_4,
    importdutystock_rule_5,
    importdutystock_rule_6,
    importdutystock_rule_7,
    importdutystock_rule_8,
    importdutystock_rule_9,
    importdutystock_rule_10,
    importdutystock_rule_11,
    importdutystock_rule_12,
    importdutystock_rule_13,
    importdutystock_rule_14,
    importdutystock_rule_15,
    importdutystock_rule_16,
    importdutystock_rule_17,
    importdutystock_rule_18,
    importdutystock_rule_19,
]
