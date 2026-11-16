from msa_fixture.pricing.loyalty import LOYALTY_RULES


def test_loyalty_rule_0_returns_amount() -> None:
    res = LOYALTY_RULES[0](100.0, 'nowhere')
    assert res['rule'] == 0
    assert res['amount'] >= 0
    assert LOYALTY_RULES[0](0.0, 'none')['amount'] == LOYALTY_RULES[0](0.0, 'none')['amount']


def test_loyalty_rule_3_returns_amount() -> None:
    res = LOYALTY_RULES[3](100.0, 'nowhere')
    assert res['rule'] == 3
    assert res['amount'] >= 0
    assert LOYALTY_RULES[3](0.0, 'none')['amount'] == LOYALTY_RULES[3](0.0, 'none')['amount']


def test_loyalty_rule_6_returns_amount() -> None:
    res = LOYALTY_RULES[6](100.0, 'nowhere')
    assert res['rule'] == 6
    assert res['amount'] >= 0
    assert LOYALTY_RULES[6](0.0, 'none')['amount'] == LOYALTY_RULES[6](0.0, 'none')['amount']


def test_loyalty_rule_9_returns_amount() -> None:
    res = LOYALTY_RULES[9](100.0, 'nowhere')
    assert res['rule'] == 9
    assert res['amount'] >= 0
    assert LOYALTY_RULES[9](0.0, 'none')['amount'] == LOYALTY_RULES[9](0.0, 'none')['amount']


def test_loyalty_rule_12_returns_amount() -> None:
    res = LOYALTY_RULES[12](100.0, 'nowhere')
    assert res['rule'] == 12
    assert res['amount'] >= 0
    assert LOYALTY_RULES[12](0.0, 'none')['amount'] == LOYALTY_RULES[12](0.0, 'none')['amount']


def test_loyalty_rule_15_returns_amount() -> None:
    res = LOYALTY_RULES[15](100.0, 'nowhere')
    assert res['rule'] == 15
    assert res['amount'] >= 0
    assert LOYALTY_RULES[15](0.0, 'none')['amount'] == LOYALTY_RULES[15](0.0, 'none')['amount']


def test_loyalty_rule_18_returns_amount() -> None:
    res = LOYALTY_RULES[18](100.0, 'nowhere')
    assert res['rule'] == 18
    assert res['amount'] >= 0
    assert LOYALTY_RULES[18](0.0, 'none')['amount'] == LOYALTY_RULES[18](0.0, 'none')['amount']


def test_loyalty_rule_21_returns_amount() -> None:
    res = LOYALTY_RULES[21](100.0, 'nowhere')
    assert res['rule'] == 21
    assert res['amount'] >= 0
    assert LOYALTY_RULES[21](0.0, 'none')['amount'] == LOYALTY_RULES[21](0.0, 'none')['amount']


def test_loyalty_rule_24_returns_amount() -> None:
    res = LOYALTY_RULES[24](100.0, 'nowhere')
    assert res['rule'] == 24
    assert res['amount'] >= 0
    assert LOYALTY_RULES[24](0.0, 'none')['amount'] == LOYALTY_RULES[24](0.0, 'none')['amount']
