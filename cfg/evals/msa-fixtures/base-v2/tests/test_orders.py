import pytest

from msa_fixture.inventory import Item, Store
from msa_fixture.orders import OrderService


def _svc() -> OrderService:
    s = Store()
    s.add(Item("a1", "bolt", 10, 0.5))
    return OrderService(s)


def test_place_reserves_stock() -> None:
    svc = _svc()
    order = svc.place("a1", 4)
    assert order["amount"] == 2.0
    assert svc.store.get("a1").qty == 6


def test_place_rejects_short_stock() -> None:
    with pytest.raises(ValueError):
        _svc().place("a1", 11)
