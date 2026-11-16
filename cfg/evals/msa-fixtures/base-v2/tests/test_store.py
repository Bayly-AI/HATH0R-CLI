from msa_fixture.inventory import Item, Store


def _store() -> Store:
    s = Store()
    s.add(Item("a1", "bolt", 10, 0.5))
    s.add(Item("b2", "nut", 4, 0.25))
    return s


def test_get_and_total() -> None:
    s = _store()
    assert s.get("a1").name == "bolt"
    assert s.total_value() == 6.0


def test_remove() -> None:
    s = _store()
    assert s.remove("b2").sku == "b2"
    assert [i.sku for i in s.items()] == ["a1"]
