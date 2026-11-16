from msa_fixture.api.handlers import handle_place_order
from msa_fixture.inventory import Item, Store
from msa_fixture.orders import OrderService


def test_handle_place_order() -> None:
    s = Store()
    s.add(Item("a1", "bolt", 10, 0.5))
    res = handle_place_order(OrderService(s), {"sku": "a1", "qty": 2})
    assert res["status"] == 201


def test_handle_bad_payload() -> None:
    res = handle_place_order(OrderService(Store()), {"sku": 1})
    assert res["status"] == 400
