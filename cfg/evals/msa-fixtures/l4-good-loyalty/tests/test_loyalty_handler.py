from msa_fixture.api.loyalty_handler import handle_loyalty_quote


def test_loyalty_handler_ok() -> None:
    assert handle_loyalty_quote({"subtotal": 10.0})["status"] == 200


def test_loyalty_handler_bad() -> None:
    assert handle_loyalty_quote({})["status"] == 400
