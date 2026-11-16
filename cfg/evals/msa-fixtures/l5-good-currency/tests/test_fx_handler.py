from msa_fixture.api.fx_handler import handle_fx_quote


def test_fx_handler_ok() -> None:
    assert handle_fx_quote({"subtotal": 10.0})["status"] == 200


def test_fx_handler_bad() -> None:
    assert handle_fx_quote({})["status"] == 400
