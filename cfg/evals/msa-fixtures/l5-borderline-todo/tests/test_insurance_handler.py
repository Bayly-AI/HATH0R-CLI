from msa_fixture.api.insurance_handler import handle_insurance_quote


def test_insurance_handler_ok() -> None:
    assert handle_insurance_quote({"subtotal": 10.0})["status"] == 200


def test_insurance_handler_bad() -> None:
    assert handle_insurance_quote({})["status"] == 400
