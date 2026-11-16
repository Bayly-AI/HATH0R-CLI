from msa_fixture.shipping import SHIPPING_RULES


def test_shipping_rule_0_returns_amount() -> None:
    res = SHIPPING_RULES[0](100.0, 'nowhere')
    assert res['rule'] == 0
    assert res['amount'] >= 0
    assert SHIPPING_RULES[0](0.0, 'none')['amount'] == SHIPPING_RULES[0](0.0, 'none')['amount']


def test_shipping_rule_3_returns_amount() -> None:
    res = SHIPPING_RULES[3](100.0, 'nowhere')
    assert res['rule'] == 3
    assert res['amount'] >= 0
    assert SHIPPING_RULES[3](0.0, 'none')['amount'] == SHIPPING_RULES[3](0.0, 'none')['amount']


def test_shipping_rule_6_returns_amount() -> None:
    res = SHIPPING_RULES[6](100.0, 'nowhere')
    assert res['rule'] == 6
    assert res['amount'] >= 0
    assert SHIPPING_RULES[6](0.0, 'none')['amount'] == SHIPPING_RULES[6](0.0, 'none')['amount']
