"""In-memory inventory store."""

from typing import Dict, List

from msa_fixture.inventory.models import Item


class Store:
    """Holds items by SKU."""

    def __init__(self) -> None:
        self._items: Dict[str, Item] = {}

    def add(self, item: Item) -> None:
        """Add or replace an item."""
        self._items[item.sku] = item

    def get(self, sku: str) -> Item:
        """Return the item for ``sku``; raises KeyError when unknown."""
        return self._items[sku]

    def remove(self, sku: str) -> Item:
        """Remove and return the item for ``sku``."""
        return self._items.pop(sku)

    def items(self) -> List[Item]:
        """All items, sorted by SKU."""
        return [self._items[k] for k in sorted(self._items)]

    def total_value(self) -> float:
        """Total stock value."""
        return sum(i.value() for i in self._items.values())
