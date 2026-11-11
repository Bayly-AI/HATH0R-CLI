from msa_fixture.calc import add


def test_add_negative() -> None:
    assert add(-1, -2) == -3
