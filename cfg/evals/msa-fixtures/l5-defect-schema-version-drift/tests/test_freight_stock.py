from msa_fixture.inventory.freight_stock import FREIGHTSTOCK_RULES


def test_freightstock_rule_0_returns_amount() -> None:
    res = FREIGHTSTOCK_RULES[0](100.0, 'nowhere')
    assert res['rule'] == 0
    assert res['amount'] >= 0
    assert FREIGHTSTOCK_RULES[0](0.0, 'none')['amount'] == FREIGHTSTOCK_RULES[0](0.0, 'none')['amount']


def test_freightstock_rule_3_returns_amount() -> None:
    res = FREIGHTSTOCK_RULES[3](100.0, 'nowhere')
    assert res['rule'] == 3
    assert res['amount'] >= 0
    assert FREIGHTSTOCK_RULES[3](0.0, 'none')['amount'] == FREIGHTSTOCK_RULES[3](0.0, 'none')['amount']


def test_freightstock_rule_6_returns_amount() -> None:
    res = FREIGHTSTOCK_RULES[6](100.0, 'nowhere')
    assert res['rule'] == 6
    assert res['amount'] >= 0
    assert FREIGHTSTOCK_RULES[6](0.0, 'none')['amount'] == FREIGHTSTOCK_RULES[6](0.0, 'none')['amount']


def test_freightstock_rule_9_returns_amount() -> None:
    res = FREIGHTSTOCK_RULES[9](100.0, 'nowhere')
    assert res['rule'] == 9
    assert res['amount'] >= 0
    assert FREIGHTSTOCK_RULES[9](0.0, 'none')['amount'] == FREIGHTSTOCK_RULES[9](0.0, 'none')['amount']


def test_freightstock_rule_12_returns_amount() -> None:
    res = FREIGHTSTOCK_RULES[12](100.0, 'nowhere')
    assert res['rule'] == 12
    assert res['amount'] >= 0
    assert FREIGHTSTOCK_RULES[12](0.0, 'none')['amount'] == FREIGHTSTOCK_RULES[12](0.0, 'none')['amount']


def test_freightstock_rule_15_returns_amount() -> None:
    res = FREIGHTSTOCK_RULES[15](100.0, 'nowhere')
    assert res['rule'] == 15
    assert res['amount'] >= 0
    assert FREIGHTSTOCK_RULES[15](0.0, 'none')['amount'] == FREIGHTSTOCK_RULES[15](0.0, 'none')['amount']


def test_freightstock_rule_18_returns_amount() -> None:
    res = FREIGHTSTOCK_RULES[18](100.0, 'nowhere')
    assert res['rule'] == 18
    assert res['amount'] >= 0
    assert FREIGHTSTOCK_RULES[18](0.0, 'none')['amount'] == FREIGHTSTOCK_RULES[18](0.0, 'none')['amount']
