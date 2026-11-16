from msa_fixture.duty import DUTY_RULES


def test_duty_rule_0_returns_amount() -> None:
    res = DUTY_RULES[0](100.0, 'nowhere')
    assert res['rule'] == 0
    assert res['amount'] >= 0
    assert DUTY_RULES[0](0.0, 'none')['amount'] == DUTY_RULES[0](0.0, 'none')['amount']


def test_duty_rule_3_returns_amount() -> None:
    res = DUTY_RULES[3](100.0, 'nowhere')
    assert res['rule'] == 3
    assert res['amount'] >= 0
    assert DUTY_RULES[3](0.0, 'none')['amount'] == DUTY_RULES[3](0.0, 'none')['amount']


def test_duty_rule_6_returns_amount() -> None:
    res = DUTY_RULES[6](100.0, 'nowhere')
    assert res['rule'] == 6
    assert res['amount'] >= 0
    assert DUTY_RULES[6](0.0, 'none')['amount'] == DUTY_RULES[6](0.0, 'none')['amount']
