"""JSON-style request handlers."""

from typing import Any, Dict

from msa_fixture.orders.service import OrderService


def handle_place_order(service: OrderService, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Validate a payload and place an order; errors become a 400 response."""
    sku = payload.get("sku")
    qty = payload.get("qty")
    if not isinstance(sku, str) or not isinstance(qty, int):
        return {"status": 400, "error": "sku (str) and qty (int) are required"}
    try:
        order = service.place(sku, qty)
    except (KeyError, ValueError) as exc:
        return {"status": 400, "error": str(exc)}
    return {"status": 201, "order": order}
