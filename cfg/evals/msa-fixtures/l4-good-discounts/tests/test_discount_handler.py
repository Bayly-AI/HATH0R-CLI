from msa_fixture.api.discount_handler import handle_discount_quote


def test_discount_handler_ok() -> None:
    assert handle_discount_quote({"subtotal": 10.0})["status"] == 200


def test_discount_handler_bad() -> None:
    assert handle_discount_quote({})["status"] == 400
