from msa_fixture.tax import TAX_RULES


def test_tax_rule_0_returns_amount() -> None:
    res = TAX_RULES[0](100.0, 'nowhere')
    assert res['rule'] == 0
    assert res['amount'] >= 0
    assert TAX_RULES[0](0.0, 'none')['amount'] == TAX_RULES[0](0.0, 'none')['amount']


def test_tax_rule_3_returns_amount() -> None:
    res = TAX_RULES[3](100.0, 'nowhere')
    assert res['rule'] == 3
    assert res['amount'] >= 0
    assert TAX_RULES[3](0.0, 'none')['amount'] == TAX_RULES[3](0.0, 'none')['amount']


def test_tax_rule_6_returns_amount() -> None:
    res = TAX_RULES[6](100.0, 'nowhere')
    assert res['rule'] == 6
    assert res['amount'] >= 0
    assert TAX_RULES[6](0.0, 'none')['amount'] == TAX_RULES[6](0.0, 'none')['amount']
