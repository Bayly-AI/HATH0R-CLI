from msa_fixture.fees import FEES_RULES


def test_fees_rule_0_returns_amount() -> None:
    res = FEES_RULES[0](100.0, 'nowhere')
    assert res['rule'] == 0
    assert res['amount'] >= 0
    assert FEES_RULES[0](0.0, 'none')['amount'] == FEES_RULES[0](0.0, 'none')['amount']


def test_fees_rule_3_returns_amount() -> None:
    res = FEES_RULES[3](100.0, 'nowhere')
    assert res['rule'] == 3
    assert res['amount'] >= 0
    assert FEES_RULES[3](0.0, 'none')['amount'] == FEES_RULES[3](0.0, 'none')['amount']


def test_fees_rule_6_returns_amount() -> None:
    res = FEES_RULES[6](100.0, 'nowhere')
    assert res['rule'] == 6
    assert res['amount'] >= 0
    assert FEES_RULES[6](0.0, 'none')['amount'] == FEES_RULES[6](0.0, 'none')['amount']
