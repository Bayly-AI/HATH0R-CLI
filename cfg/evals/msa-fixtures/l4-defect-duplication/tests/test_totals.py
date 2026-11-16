from msa_fixture.orders.totals import order_totals


def test_totals() -> None:
    assert order_totals([1.0], [2.0]) == 2.0
