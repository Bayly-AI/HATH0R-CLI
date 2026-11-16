from msa_fixture.api.rebate_handler import handle_rebate_quote


def test_rebate_handler_ok() -> None:
    assert handle_rebate_quote({"subtotal": 10.0})["status"] == 200


def test_rebate_handler_bad() -> None:
    assert handle_rebate_quote({})["status"] == 400
