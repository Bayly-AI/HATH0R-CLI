from msa_fixture.api.bundle_handler import handle_bundle_quote


def test_bundle_handler_ok() -> None:
    assert handle_bundle_quote({"subtotal": 10.0})["status"] == 200


def test_bundle_handler_bad() -> None:
    assert handle_bundle_quote({})["status"] == 400
