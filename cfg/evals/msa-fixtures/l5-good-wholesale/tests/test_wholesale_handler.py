from msa_fixture.api.wholesale_handler import handle_wholesale_quote


def test_wholesale_handler_ok() -> None:
    assert handle_wholesale_quote({"subtotal": 10.0})["status"] == 200


def test_wholesale_handler_bad() -> None:
    assert handle_wholesale_quote({})["status"] == 400
