"""Order placement."""

from typing import Dict, List

from msa_fixture.inventory.store import Store


class OrderService:
    """Places orders and reserves stock."""

    def __init__(self, store: Store) -> None:
        self.store = store
        self.placed: List[Dict[str, object]] = []

    def place(self, sku: str, qty: int) -> Dict[str, object]:
        """Reserve ``qty`` of ``sku``; raises ValueError when stock is short."""
        if qty <= 0:
            raise ValueError("quantity must be positive")
        item = self.store.get(sku)
        if item.qty < qty:
            raise ValueError(f"only {item.qty} of {sku} in stock")
        item.qty -= qty
        order = {"id": len(self.placed) + 1, "sku": sku, "qty": qty, "amount": round(qty * item.price, 2)}
        self.placed.append(order)
        return order
