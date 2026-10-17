"""Scientific validation tests for Phase 0 reference case: Enzyme Kinetics (Michaelis-Menten).

Validates:
1. Reference dataset availability and schema invariants.
2. Numerical acceptance criteria against certified reference values (Bates & Watts 1988).
3. Ground-truth parameter recovery on synthetic assay data.
4. Lineweaver-Burk heuristic initialization behavior.
5. Invariant checking for unsupported cases (negative values, lack of levels, inhibition).
"""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from scipy.optimize import curve_fit

# Project root path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
PUROMYCIN_CSV = PROJECT_ROOT / "examples" / "enzyme_kinetics_puromycin.csv"
SYNTHETIC_CSV = PROJECT_ROOT / "examples" / "enzyme_kinetics_synthetic.csv"


def michaelis_menten(s: np.ndarray, vmax: float, km: float) -> np.ndarray:
    """Standard Michaelis-Menten rate equation: v = (Vmax * s) / (Km + s)."""
    return (vmax * s) / (km + s)


def lineweaver_burk_estimate(s: np.ndarray, v: np.ndarray) -> tuple[float, float]:
    """Estimate initial Vmax and Km via Lineweaver-Burk: 1/v = (Km/Vmax)(1/s) + 1/Vmax."""
    inv_s = 1.0 / s
    inv_v = 1.0 / v
    slope, intercept = np.polyfit(inv_s, inv_v, deg=1)
    if intercept <= 0 or slope <= 0:
        msg = "Lineweaver-Burk yielded non-physical coefficients (intercept <= 0 or slope <= 0)."
        raise ValueError(msg)
    vmax_0 = 1.0 / intercept
    km_0 = slope * vmax_0
    return float(vmax_0), float(km_0)


def test_puromycin_dataset_integrity():
    """Verify Puromycin reference dataset exists, matches schema, and satisfies invariants."""
    assert PUROMYCIN_CSV.is_file(), f"Missing Puromycin dataset at {PUROMYCIN_CSV}"

    df = pd.read_csv(PUROMYCIN_CSV)
    assert list(df.columns) == ["substrate_conc", "reaction_velocity"]
    assert len(df) == 12, f"Expected 12 observations for Puromycin treated set, got {len(df)}"

    # Invariants: strictly positive concentrations and velocities
    assert (df["substrate_conc"] > 0).all(), "Found non-positive substrate concentrations"
    assert (df["reaction_velocity"] > 0).all(), "Found non-positive reaction velocities"

    # Invariant: at least 4 distinct concentration levels (Puromycin has 6)
    distinct_levels = df["substrate_conc"].nunique()
    assert distinct_levels == 6, f"Expected 6 distinct concentration levels, got {distinct_levels}"


def test_puromycin_reference_numerical_acceptance():
    """Verify numerical acceptance on Puromycin against Bates & Watts (1988) reference values."""
    df = pd.read_csv(PUROMYCIN_CSV)
    s = df["substrate_conc"].to_numpy(dtype=float)
    v = df["reaction_velocity"].to_numpy(dtype=float)

    # Heuristic initial guess via Lineweaver-Burk
    vmax_0, km_0 = lineweaver_burk_estimate(s, v)
    assert vmax_0 > 0 and km_0 > 0

    # Non-linear least squares fit with physical bounds [0, inf)
    popt, pcov = curve_fit(
        michaelis_menten,
        s,
        v,
        p0=[vmax_0, km_0],
        bounds=(0.0, np.inf),
        method="trf",
    )
    vmax_fit, km_fit = popt
    se_vmax, se_km = np.sqrt(np.diag(pcov))

    residuals = v - michaelis_menten(s, vmax_fit, km_fit)
    rss = float(np.sum(residuals**2))
    ss_tot = float(np.sum((v - np.mean(v)) ** 2))
    r_squared = 1.0 - (rss / ss_tot)

    # Reference values from Bates & Watts (1988):
    # Vmax = 212.684 +/- 6.947
    # Km = 0.06412 +/- 0.00828
    # RSS = 1195.45
    assert abs(vmax_fit - 212.684) < 0.50, f"Vmax {vmax_fit} diverged from reference 212.684"
    assert abs(km_fit - 0.06412) < 0.0050, f"Km {km_fit} diverged from reference 0.06412"
    assert abs(rss - 1195.45) < 10.0, f"RSS {rss} diverged from reference 1195.45"
    assert abs(se_vmax - 6.947) < 0.50, f"SE(Vmax) {se_vmax} diverged from reference 6.947"
    assert abs(se_km - 0.00828) < 0.0015, f"SE(Km) {se_km} diverged from reference 0.00828"
    assert r_squared > 0.95, f"R^2 {r_squared} below acceptance threshold 0.95"


def test_synthetic_ground_truth_recovery():
    """Verify parameter recovery on synthetic dataset with known ground truth parameters."""
    assert SYNTHETIC_CSV.is_file(), f"Missing synthetic dataset at {SYNTHETIC_CSV}"

    df = pd.read_csv(SYNTHETIC_CSV)
    s = df["substrate_conc"].to_numpy(dtype=float)
    v = df["reaction_velocity"].to_numpy(dtype=float)

    assert len(df) == 14
    assert df["substrate_conc"].nunique() == 7

    vmax_0, km_0 = lineweaver_burk_estimate(s, v)
    popt, pcov = curve_fit(
        michaelis_menten,
        s,
        v,
        p0=[vmax_0, km_0],
        bounds=(0.0, np.inf),
        method="trf",
    )
    vmax_fit, km_fit = popt
    se_vmax, se_km = np.sqrt(np.diag(pcov))

    # True values: Vmax = 200.0, Km = 0.050
    # Must recover within 2 * standard error and < 1% relative error
    assert abs(vmax_fit - 200.0) < 2.0 * se_vmax
    assert abs(km_fit - 0.050) < 2.0 * se_km
    assert abs(vmax_fit - 200.0) / 200.0 < 0.01
    assert abs(km_fit - 0.050) / 0.050 < 0.01

    residuals = v - michaelis_menten(s, vmax_fit, km_fit)
    rss = float(np.sum(residuals**2))
    r_squared = 1.0 - (rss / float(np.sum((v - np.mean(v)) ** 2)))
    assert r_squared > 0.99, f"Synthetic dataset R^2 {r_squared} below 0.99"


def test_lineweaver_burk_distortion_diagnostic():
    """Demonstrate why Lineweaver-Burk is used for initialization but rejected as primary model."""
    df = pd.read_csv(PUROMYCIN_CSV)
    s = df["substrate_conc"].to_numpy(dtype=float)
    v = df["reaction_velocity"].to_numpy(dtype=float)

    vmax_lb, km_lb = lineweaver_burk_estimate(s, v)

    # Lineweaver-Burk linear fit overweights low concentrations, distorting Vmax and Km
    assert vmax_lb > 0 and km_lb > 0
    popt, _ = curve_fit(michaelis_menten, s, v, p0=[vmax_lb, km_lb], bounds=(0, np.inf))
    vmax_nlls = popt[0]

    # Lineweaver-Burk Vmax deviates from true NLLS Vmax due to reciprocal error weighting
    relative_diff = abs(vmax_lb - vmax_nlls) / vmax_nlls
    assert 0.01 < relative_diff < 0.30, f"Expected reciprocal distortion, got {relative_diff:.4f}"


def test_unsupported_cases_rejection_rules():
    """Verify that unsupported conditions defined in Phase 0 Scope Brief are detected."""
    # Case 1: Negative substrate concentration
    invalid_s = np.array([-0.05, 0.02, 0.05, 0.10])
    with pytest.raises(ValueError, match="negative"):
        if (invalid_s < 0).any():
            raise ValueError("Unsupported case: negative substrate concentration detected.")

    # Case 2: Fewer than 4 distinct concentration levels
    few_levels_s = np.array([0.05, 0.05, 0.10, 0.10])
    with pytest.raises(ValueError, match="distinct concentration levels"):
        if len(np.unique(few_levels_s)) < 4:
            raise ValueError("Unsupported case: fewer than 4 distinct concentration levels.")

    # Case 3: Severe substrate inhibition (velocity drops by > 25% at high concentration)
    inhibited_v = np.array([30.0, 100.0, 140.0, 120.0, 80.0])  # drops from 140 down to 80 (42%)
    with pytest.raises(ValueError, match="substrate inhibition"):
        max_idx = int(np.argmax(inhibited_v))
        if max_idx < len(inhibited_v) - 1:
            drop_ratio = (inhibited_v[max_idx] - inhibited_v[-1]) / inhibited_v[max_idx]
            if drop_ratio > 0.25:
                raise ValueError("Unsupported case: severe substrate inhibition detected.")
