import pytest

from msa_fixture.calc import divide


def test_divide_by_zero_raises() -> None:
    with pytest.raises(ValueError):
        divide(1, 0)
