"""Quote handler for the carbon rules."""

from typing import Any, Dict

from msa_fixture.orders.carbon_quote import quote_carbon


def handle_carbon_quote(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Return a quote or a 400 response."""
    subtotal = payload.get("subtotal")
    if not isinstance(subtotal, (int, float)):
        return {"status": 400, "error": "subtotal is required"}
    return {"status": 200, "lines": quote_carbon(float(subtotal), str(payload.get("region", "")))}
