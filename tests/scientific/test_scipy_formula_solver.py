"""Scientific validation tests for the generic ScipyFormulaSolver."""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from scimodel.adapters.scipy_formula_solver import ScipyFormulaSolver
from scimodel.domain.fit import ModelFitError
from scimodel.domain.formula import ModelFormula, ParameterSpec

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PUROMYCIN_CSV = PROJECT_ROOT / "examples" / "enzyme_kinetics_puromycin.csv"
SYNTHETIC_CSV = PROJECT_ROOT / "examples" / "enzyme_kinetics_synthetic.csv"


def test_scipy_formula_solver_puromycin_reference() -> None:
    """ScipyFormulaSolver reproduces Bates & Watts (1988) certified parameters on Puromycin."""
    df = pd.read_csv(PUROMYCIN_CSV)
    s = df["substrate_conc"].to_numpy(dtype=float)
    v = df["reaction_velocity"].to_numpy(dtype=float)

    mm_formula = ModelFormula(
        name="michaelis_menten",
        expression="(Vmax * s) / (Km + s)",
        parameters=[
            ParameterSpec("Vmax", lower_bound=0.0, initial_guess=200.0),
            ParameterSpec("Km", lower_bound=0.0, initial_guess=0.05),
        ],
        independent_vars=["s"],
        dependent_var="v",
    )

    solver = ScipyFormulaSolver()
    assert solver.backend_name == "scipy"
    assert solver.is_available() is True

    result = solver.fit(mm_formula, s, v)

    assert result.converged is True
    # Reference values: Vmax = 212.684, Km = 0.06412, RSS = 1195.45
    assert abs(result.parameters["Vmax"] - 212.684) < 0.50
    assert abs(result.parameters["Km"] - 0.06412) < 0.0050
    assert abs(result.metrics["rss"] - 1195.45) < 10.0
    assert result.metrics["r_squared"] > 0.95
    assert abs(result.standard_errors["Vmax"] - 6.947) < 0.50
    assert abs(result.standard_errors["Km"] - 0.00828) < 0.0015


def test_scipy_formula_solver_synthetic_recovery() -> None:
    """ScipyFormulaSolver recovers true parameters (200.0, 0.05) on synthetic dataset."""
    df = pd.read_csv(SYNTHETIC_CSV)
    s = df["substrate_conc"].to_numpy(dtype=float)
    v = df["reaction_velocity"].to_numpy(dtype=float)

    mm_formula = ModelFormula(
        name="michaelis_menten",
        expression="(Vmax * s) / (Km + s)",
        parameters=[
            ParameterSpec("Vmax", lower_bound=0.0),
            ParameterSpec("Km", lower_bound=0.0),
        ],
        independent_vars=["s"],
    )

    solver = ScipyFormulaSolver()
    result = solver.fit(mm_formula, s, v)

    assert result.converged is True
    assert abs(result.parameters["Vmax"] - 200.0) < 2.0
    assert abs(result.parameters["Km"] - 0.050) < 0.002
    assert result.metrics["r_squared"] > 0.99


def test_scipy_formula_solver_exponential_decay() -> None:
    """ScipyFormulaSolver fits an exponential decay formula C0 * exp(-k * t)."""
    t_data = np.array([0.0, 1.0, 2.0, 4.0, 8.0, 12.0], dtype=float)
    # Ground truth: C0 = 50.0, k = 0.25
    c_data = 50.0 * np.exp(-0.25 * t_data) + np.array([0.1, -0.1, 0.05, -0.05, 0.02, -0.02])

    decay_formula = ModelFormula(
        name="first_order_decay",
        expression="C0 * exp(-k * t)",
        parameters=[
            ParameterSpec("C0", lower_bound=0.0, initial_guess=40.0),
            ParameterSpec("k", lower_bound=0.0, initial_guess=0.1),
        ],
        independent_vars=["t"],
    )

    solver = ScipyFormulaSolver()
    result = solver.fit(decay_formula, t_data, c_data)

    assert result.converged is True
    assert abs(result.parameters["C0"] - 50.0) < 0.5
    assert abs(result.parameters["k"] - 0.25) < 0.01
    assert result.metrics["r_squared"] > 0.999


def test_scipy_formula_solver_rejects_insufficient_data() -> None:
    """ScipyFormulaSolver rejects data with fewer observations than parameters + 1."""
    x = np.array([1.0, 2.0])
    y = np.array([10.0, 20.0])
    formula = ModelFormula(
        name="quadratic",
        expression="a * (x ** 2) + b * x + c",
        parameters=[ParameterSpec("a"), ParameterSpec("b"), ParameterSpec("c")],
        independent_vars=["x"],
    )
    solver = ScipyFormulaSolver()
    with pytest.raises(ModelFitError, match="At least 4 observations are required"):
        solver.fit(formula, x, y)
