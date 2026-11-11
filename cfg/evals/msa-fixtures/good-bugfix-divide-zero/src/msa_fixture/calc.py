"""Tiny calculator used as a measured part in the Hath0r MSA panel."""


def add(a: float, b: float) -> float:
    """Return a + b."""
    return a + b


def divide(a: float, b: float) -> float:
    """Return a / b; raise ValueError on division by zero."""
    if b == 0:
        raise ValueError("division by zero")
    return a / b
