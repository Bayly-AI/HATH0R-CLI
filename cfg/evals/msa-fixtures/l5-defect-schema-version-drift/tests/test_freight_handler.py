from msa_fixture.api.freight_handler import handle_freight_quote


def test_freight_handler_ok() -> None:
    assert handle_freight_quote({"subtotal": 10.0})["status"] == 200


def test_freight_handler_bad() -> None:
    assert handle_freight_quote({})["status"] == 400
