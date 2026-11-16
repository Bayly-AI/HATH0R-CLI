"""Inventory data model."""

from dataclasses import dataclass


@dataclass
class Item:
    """A stock-keeping unit held in the store."""

    sku: str
    name: str
    qty: int
    price: float

    def value(self) -> float:
        """Stock value of this item."""
        return self.qty * self.price
