from msa_fixture.api.excise_handler import handle_excise_quote


def test_excise_handler_ok() -> None:
    assert handle_excise_quote({"subtotal": 10.0})["status"] == 200


def test_excise_handler_bad() -> None:
    assert handle_excise_quote({})["status"] == 400
