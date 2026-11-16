from msa_fixture.api.clearance_handler import handle_clearance_quote


def test_clearance_handler_ok() -> None:
    assert handle_clearance_quote({"subtotal": 10.0})["status"] == 200


def test_clearance_handler_bad() -> None:
    assert handle_clearance_quote({})["status"] == 400
