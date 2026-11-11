from msa_fixture.calc import subtract


def test_subtract() -> None:
    assert subtract(5, 3) == 2
