import pytest

from msa_fixture.stats import mean, value_range, variance


def test_mean() -> None:
    assert mean([1, 2, 3]) == 2


def test_variance() -> None:
    assert variance([1, 2, 3]) == 1


def test_range() -> None:
    assert value_range([4, 1, 9]) == 8


def test_empty() -> None:
    with pytest.raises(ValueError):
        mean([])
