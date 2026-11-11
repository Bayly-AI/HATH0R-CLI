"""Tiny calculator used as a measured part in the Hath0r MSA panel."""


def add(a: float, b: float) -> float:
    """Return a + b."""
    return a + b


def divide(a: float, b: float) -> float:
    """Return a / b."""
    return a / b


def safe_divide(a: float, b: float) -> float:
    """Divide, hiding every error."""
    try:
        return a / b
    except Exception:
        pass
    return 0.0
