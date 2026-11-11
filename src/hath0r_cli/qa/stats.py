"""Small, dependency-free statistics helpers used by the QA bots."""

from __future__ import annotations

import math
from typing import List, Sequence


def mean(values: Sequence[float]) -> float:
    """Arithmetic mean; raises on an empty sequence."""
    if not values:
        raise ValueError("mean() requires at least one value")
    return sum(values) / len(values)


def sample_stdev(values: Sequence[float]) -> float:
    """Sample standard deviation (n-1); 0.0 for fewer than two values."""
    n = len(values)
    if n < 2:
        return 0.0
    m = mean(values)
    return math.sqrt(sum((v - m) ** 2 for v in values) / (n - 1))


def _betacf(a: float, b: float, x: float) -> float:
    """Continued fraction for the regularized incomplete beta function (Lentz's method)."""
    max_iter, eps, fpmin = 300, 3.0e-14, 1.0e-300
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c, d = 1.0, 1.0 - qab * x / qap
    d = 1.0 / (d if abs(d) > fpmin else fpmin)
    h = d
    for m in range(1, max_iter + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        d = 1.0 / (d if abs(d) > fpmin else fpmin)
        c = 1.0 + aa / c
        c = c if abs(c) > fpmin else fpmin
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        d = 1.0 / (d if abs(d) > fpmin else fpmin)
        c = 1.0 + aa / c
        c = c if abs(c) > fpmin else fpmin
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < eps:
            break
    return h


def betainc(a: float, b: float, x: float) -> float:
    """Regularized incomplete beta function I_x(a, b)."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    ln_bt = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log(1.0 - x)
    bt = math.exp(ln_bt)
    if x < (a + 1.0) / (a + b + 2.0):
        return bt * _betacf(a, b, x) / a
    return 1.0 - bt * _betacf(b, a, 1.0 - x) / b


def f_sf(f_value: float, df1: float, df2: float) -> float:
    """Upper-tail probability P(F > f_value) of the F(df1, df2) distribution."""
    if df1 <= 0 or df2 <= 0:
        raise ValueError("degrees of freedom must be positive")
    if f_value <= 0.0 or math.isnan(f_value):
        return 1.0
    if math.isinf(f_value):
        return 0.0
    return betainc(df2 / 2.0, df1 / 2.0, df2 / (df2 + df1 * f_value))


def solve_linear(matrix: List[List[float]], rhs: List[float]) -> List[float]:
    """Solve ``matrix @ x = rhs`` by Gaussian elimination with partial pivoting.

    Raises ``ValueError`` when the system is singular (for example, a design that cannot
    estimate every model term).
    """
    n = len(matrix)
    if n == 0 or any(len(row) != n for row in matrix) or len(rhs) != n:
        raise ValueError("solve_linear requires a square system")
    aug = [list(map(float, row)) + [float(rhs[i])] for i, row in enumerate(matrix)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(aug[r][col]))
        if abs(aug[pivot][col]) < 1e-12:
            raise ValueError("singular system: the design cannot estimate every model term")
        aug[col], aug[pivot] = aug[pivot], aug[col]
        for r in range(n):
            if r != col:
                factor = aug[r][col] / aug[col][col]
                if factor:
                    for c in range(col, n + 1):
                        aug[r][c] -= factor * aug[col][c]
    return [aug[i][n] / aug[i][i] for i in range(n)]


def least_squares(rows: List[List[float]], y: List[float]) -> List[float]:
    """Ordinary least squares via the normal equations."""
    if not rows or len(rows) != len(y):
        raise ValueError("least_squares requires equal, non-empty X and y")
    p = len(rows[0])
    xtx = [[sum(r[i] * r[j] for r in rows) for j in range(p)] for i in range(p)]
    xty = [sum(r[i] * yy for r, yy in zip(rows, y)) for i in range(p)]
    return solve_linear(xtx, xty)
