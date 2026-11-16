from msa_fixture.api.promo_handler import handle_promo_quote


def test_promo_handler_ok() -> None:
    assert handle_promo_quote({"subtotal": 10.0})["status"] == 200


def test_promo_handler_bad() -> None:
    assert handle_promo_quote({})["status"] == 400
