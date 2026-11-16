from msa_fixture.api.importduty_handler import handle_importduty_quote


def test_importduty_handler_ok() -> None:
    assert handle_importduty_quote({"subtotal": 10.0})["status"] == 200


def test_importduty_handler_bad() -> None:
    assert handle_importduty_quote({})["status"] == 400
