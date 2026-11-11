from msa_fixture.calc import safe_divide


def test_safe_divide() -> None:
    assert safe_divide(4, 2) == 2
