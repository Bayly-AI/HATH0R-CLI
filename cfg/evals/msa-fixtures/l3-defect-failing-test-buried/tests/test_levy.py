from msa_fixture.levy import LEVY_RULES


def test_levy_rule_0_returns_amount() -> None:
    res = LEVY_RULES[0](100.0, 'nowhere')
    assert res['rule'] == 0
    assert res['amount'] >= 0
    assert LEVY_RULES[0](0.0, 'none')['amount'] == -1.0


def test_levy_rule_3_returns_amount() -> None:
    res = LEVY_RULES[3](100.0, 'nowhere')
    assert res['rule'] == 3
    assert res['amount'] >= 0
    assert LEVY_RULES[3](0.0, 'none')['amount'] == LEVY_RULES[3](0.0, 'none')['amount']


def test_levy_rule_6_returns_amount() -> None:
    res = LEVY_RULES[6](100.0, 'nowhere')
    assert res['rule'] == 6
    assert res['amount'] >= 0
    assert LEVY_RULES[6](0.0, 'none')['amount'] == LEVY_RULES[6](0.0, 'none')['amount']
