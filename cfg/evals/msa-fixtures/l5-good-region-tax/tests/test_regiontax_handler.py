from msa_fixture.api.regiontax_handler import handle_regiontax_quote


def test_regiontax_handler_ok() -> None:
    assert handle_regiontax_quote({"subtotal": 10.0})["status"] == 200


def test_regiontax_handler_bad() -> None:
    assert handle_regiontax_quote({})["status"] == 400
