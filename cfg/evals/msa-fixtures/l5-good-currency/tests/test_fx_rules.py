from msa_fixture.pricing.fx import FX_RULES


def test_fx_rule_0_returns_amount() -> None:
    res = FX_RULES[0](100.0, 'nowhere')
    assert res['rule'] == 0
    assert res['amount'] >= 0
    assert FX_RULES[0](0.0, 'none')['amount'] == FX_RULES[0](0.0, 'none')['amount']


def test_fx_rule_3_returns_amount() -> None:
    res = FX_RULES[3](100.0, 'nowhere')
    assert res['rule'] == 3
    assert res['amount'] >= 0
    assert FX_RULES[3](0.0, 'none')['amount'] == FX_RULES[3](0.0, 'none')['amount']


def test_fx_rule_6_returns_amount() -> None:
    res = FX_RULES[6](100.0, 'nowhere')
    assert res['rule'] == 6
    assert res['amount'] >= 0
    assert FX_RULES[6](0.0, 'none')['amount'] == FX_RULES[6](0.0, 'none')['amount']


def test_fx_rule_9_returns_amount() -> None:
    res = FX_RULES[9](100.0, 'nowhere')
    assert res['rule'] == 9
    assert res['amount'] >= 0
    assert FX_RULES[9](0.0, 'none')['amount'] == FX_RULES[9](0.0, 'none')['amount']


def test_fx_rule_12_returns_amount() -> None:
    res = FX_RULES[12](100.0, 'nowhere')
    assert res['rule'] == 12
    assert res['amount'] >= 0
    assert FX_RULES[12](0.0, 'none')['amount'] == FX_RULES[12](0.0, 'none')['amount']


def test_fx_rule_15_returns_amount() -> None:
    res = FX_RULES[15](100.0, 'nowhere')
    assert res['rule'] == 15
    assert res['amount'] >= 0
    assert FX_RULES[15](0.0, 'none')['amount'] == FX_RULES[15](0.0, 'none')['amount']


def test_fx_rule_18_returns_amount() -> None:
    res = FX_RULES[18](100.0, 'nowhere')
    assert res['rule'] == 18
    assert res['amount'] >= 0
    assert FX_RULES[18](0.0, 'none')['amount'] == FX_RULES[18](0.0, 'none')['amount']


def test_fx_rule_21_returns_amount() -> None:
    res = FX_RULES[21](100.0, 'nowhere')
    assert res['rule'] == 21
    assert res['amount'] >= 0
    assert FX_RULES[21](0.0, 'none')['amount'] == FX_RULES[21](0.0, 'none')['amount']


def test_fx_rule_24_returns_amount() -> None:
    res = FX_RULES[24](100.0, 'nowhere')
    assert res['rule'] == 24
    assert res['amount'] >= 0
    assert FX_RULES[24](0.0, 'none')['amount'] == FX_RULES[24](0.0, 'none')['amount']


def test_fx_rule_27_returns_amount() -> None:
    res = FX_RULES[27](100.0, 'nowhere')
    assert res['rule'] == 27
    assert res['amount'] >= 0
    assert FX_RULES[27](0.0, 'none')['amount'] == FX_RULES[27](0.0, 'none')['amount']


def test_fx_rule_30_returns_amount() -> None:
    res = FX_RULES[30](100.0, 'nowhere')
    assert res['rule'] == 30
    assert res['amount'] >= 0
    assert FX_RULES[30](0.0, 'none')['amount'] == FX_RULES[30](0.0, 'none')['amount']


def test_fx_rule_33_returns_amount() -> None:
    res = FX_RULES[33](100.0, 'nowhere')
    assert res['rule'] == 33
    assert res['amount'] >= 0
    assert FX_RULES[33](0.0, 'none')['amount'] == FX_RULES[33](0.0, 'none')['amount']


def test_fx_rule_36_returns_amount() -> None:
    res = FX_RULES[36](100.0, 'nowhere')
    assert res['rule'] == 36
    assert res['amount'] >= 0
    assert FX_RULES[36](0.0, 'none')['amount'] == FX_RULES[36](0.0, 'none')['amount']


def test_fx_rule_39_returns_amount() -> None:
    res = FX_RULES[39](100.0, 'nowhere')
    assert res['rule'] == 39
    assert res['amount'] >= 0
    assert FX_RULES[39](0.0, 'none')['amount'] == FX_RULES[39](0.0, 'none')['amount']
