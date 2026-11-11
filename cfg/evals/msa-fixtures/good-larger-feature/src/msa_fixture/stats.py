"""Descriptive statistics helpers for the MSA fixture."""

from collections.abc import Sequence


def mean(values: Sequence[float]) -> float:
    """Arithmetic mean."""
    if not values:
        raise ValueError("mean of empty sequence")
    return sum(values) / len(values)


def variance(values: Sequence[float]) -> float:
    """Sample variance."""
    if len(values) < 2:
        raise ValueError("variance needs two values")
    m = mean(values)
    return sum((v - m) ** 2 for v in values) / (len(values) - 1)


def value_range(values: Sequence[float]) -> float:
    """Max minus min."""
    if not values:
        raise ValueError("range of empty sequence")
    return max(values) - min(values)
