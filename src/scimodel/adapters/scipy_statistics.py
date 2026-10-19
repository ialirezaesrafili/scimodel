"""Statistical tests used by quality assessment, implemented with SciPy."""

from __future__ import annotations

import math
from typing import TypeAlias

import numpy as np
import numpy.typing as npt
from scipy import stats

FloatArray: TypeAlias = npt.NDArray[np.float64]


def shapiro_p_value(residuals: FloatArray) -> float | None:
    """Shapiro–Wilk normality p-value, or None when the sample is unsuitable."""
    if len(residuals) < 8 or float(np.std(residuals)) == 0.0:
        return None
    sample = residuals if len(residuals) <= 5000 else residuals[:5000]
    return float(stats.shapiro(sample).pvalue)


def spearman(x: FloatArray, y: FloatArray) -> tuple[float, float]:
    """Spearman rank correlation and p-value (NaN-safe for constant inputs)."""
    if len(x) < 3 or np.ptp(x) == 0 or np.ptp(y) == 0:
        return 0.0, 1.0
    result = stats.spearmanr(x, y)
    rho = float(result.statistic)
    p_value = float(result.pvalue)
    return (0.0 if math.isnan(rho) else rho), (1.0 if math.isnan(p_value) else p_value)


def pearson(x: FloatArray, y: FloatArray) -> float:
    if len(x) < 3 or np.ptp(x) == 0 or np.ptp(y) == 0:
        return 0.0
    return float(np.corrcoef(x, y)[0, 1])


def runs_test_p_value(residuals: FloatArray) -> float | None:
    """Wald–Wolfowitz runs test on residual signs (two-sided normal approximation)."""
    signs = np.sign(residuals[residuals != 0])
    n_pos = int(np.sum(signs > 0))
    n_neg = int(np.sum(signs < 0))
    n = n_pos + n_neg
    if n_pos < 2 or n_neg < 2 or n < 10:
        return None
    runs = 1 + int(np.count_nonzero(signs[1:] != signs[:-1]))
    expected = 2.0 * n_pos * n_neg / n + 1.0
    variance = 2.0 * n_pos * n_neg * (2.0 * n_pos * n_neg - n) / (n**2 * (n - 1.0))
    if variance <= 0:
        return None
    z = (runs - expected) / math.sqrt(variance)
    return float(2.0 * stats.norm.sf(abs(z)))


def durbin_watson(residuals: FloatArray) -> float | None:
    denominator = float(np.sum(residuals**2))
    if len(residuals) < 3 or denominator == 0.0:
        return None
    return float(np.sum(np.diff(residuals) ** 2) / denominator)


def f_test_p_value(f_statistic: float, df_numerator: int, df_denominator: int) -> float:
    if df_numerator <= 0 or df_denominator <= 0 or not math.isfinite(f_statistic):
        return float("nan")
    return float(stats.f.sf(f_statistic, df_numerator, df_denominator))


def t_critical(degrees_of_freedom: int, confidence: float = 0.95) -> float:
    return float(stats.t.ppf(0.5 + confidence / 2.0, degrees_of_freedom))


def skewness(values: FloatArray) -> float:
    if len(values) < 3 or float(np.std(values)) == 0.0:
        return 0.0
    return float(stats.skew(values))
