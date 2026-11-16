from msa_fixture.estimator import shipping_cost


def test_shipping_cost() -> None:
    assert shipping_cost(1.0, 'north', True, True, False) == 5.0
