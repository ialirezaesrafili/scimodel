"""Unit tests for the MATLAB Engine adapter and expression translator."""

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from scimodel.adapters.matlab_solver import (
    MatlabFormulaSolver,
    MatlabUnavailableError,
    translate_formula_to_matlab,
)
from scimodel.domain.formula import ModelFormula, ParameterSpec


def test_translate_michaelis_menten_to_matlab() -> None:
    """Translate Michaelis-Menten expression to vectorized MATLAB anonymous function."""
    formula = ModelFormula(
        name="michaelis_menten",
        expression="(Vmax * s) / (Km + s)",
        parameters=[ParameterSpec("Vmax"), ParameterSpec("Km")],
        independent_vars=["s"],
    )

    matlab_expr = translate_formula_to_matlab(formula)
    assert matlab_expr == "@(p, s) (p(1) .* s) ./ (p(2) + s)"


def test_translate_hill_equation_to_matlab() -> None:
    """Translate Hill equation with exponentiation (**) to MATLAB (.^)."""
    formula = ModelFormula(
        name="hill",
        expression="(Vmax * (s ** n)) / ((Khalf ** n) + (s ** n))",
        parameters=[ParameterSpec("Vmax"), ParameterSpec("Khalf"), ParameterSpec("n")],
        independent_vars=["s"],
    )

    matlab_expr = translate_formula_to_matlab(formula)
    assert matlab_expr == "@(p, s) (p(1) .* (s .^ p(3))) ./ ((p(2) .^ p(3)) + (s .^ p(3)))"


def test_matlab_solver_availability_check() -> None:
    """MatlabFormulaSolver.is_available() checks environment without raising exceptions."""
    solver = MatlabFormulaSolver()
    assert solver.backend_name == "matlab"
    # In an environment without MATLAB Engine, this must return False cleanly
    available = solver.is_available()
    assert isinstance(available, bool)


def test_matlab_solver_raises_unavailable_error() -> None:
    """Raise MatlabUnavailableError with guidance when MATLAB engine is not installed."""
    solver = MatlabFormulaSolver(fallback_to_scipy=False)
    formula = ModelFormula(
        name="linear",
        expression="m * x + b",
        parameters=[ParameterSpec("m"), ParameterSpec("b")],
        independent_vars=["x"],
    )
    x = np.array([1.0, 2.0, 3.0, 4.0])
    y = np.array([2.0, 4.0, 6.0, 8.0])

    if not solver.is_available():
        with pytest.raises(
            MatlabUnavailableError, match="MATLAB Engine API for Python is not installed"
        ):
            solver.fit(formula, x, y)


def test_matlab_solver_fallback_to_scipy() -> None:
    """When fallback_to_scipy is True, fall back gracefully to ScipyFormulaSolver."""
    solver = MatlabFormulaSolver(fallback_to_scipy=True)
    formula = ModelFormula(
        name="linear",
        expression="m * x + b",
        parameters=[ParameterSpec("m", lower_bound=-10.0), ParameterSpec("b", lower_bound=-10.0)],
        independent_vars=["x"],
    )
    x = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    y = 2.0 * x + 1.0

    result = solver.fit(formula, x, y)
    assert result.converged is True
    assert abs(result.parameters["m"] - 2.0) < 1e-4
    assert abs(result.parameters["b"] - 1.0) < 1e-4


def test_matlab_solver_mocked_execution() -> None:
    """Verify MATLAB solver execution, parameter parsing, and engine quit using mock."""
    solver = MatlabFormulaSolver()
    formula = ModelFormula(
        name="michaelis_menten",
        expression="(Vmax * s) / (Km + s)",
        parameters=[ParameterSpec("Vmax"), ParameterSpec("Km")],
        independent_vars=["s"],
    )
    x = np.array([0.1, 0.5, 1.0, 2.0], dtype=float)
    y = np.array([10.0, 30.0, 50.0, 60.0], dtype=float)

    mock_matlab = MagicMock()
    mock_matlab.double.side_effect = lambda val: val
    mock_engine_mod = MagicMock()
    mock_matlab.engine = mock_engine_mod
    mock_eng = MagicMock()
    mock_eng.eval.return_value = "mock_f_handle"
    mock_eng.lsqcurvefit.return_value = (
        [200.0, 0.05],
        10.5,
        [],
        1,
        {"funcCount": 15},
        [],
        [],
    )
    mock_engine_mod.start_matlab.return_value = mock_eng

    with (
        patch("scimodel.adapters.matlab_solver.is_matlab_engine_installed", return_value=True),
        patch.dict("sys.modules", {"matlab": mock_matlab, "matlab.engine": mock_engine_mod}),
    ):
        result = solver.fit(formula, x, y)
        assert result.converged is True
        assert result.parameters["Vmax"] == 200.0
        assert result.parameters["Km"] == 0.05
        assert result.function_evaluations == 15
        mock_eng.quit.assert_called_once()


def test_matlab_solver_engine_startup_failure() -> None:
    """Handle engine startup failure with MatlabUnavailableError."""
    solver = MatlabFormulaSolver()
    formula = ModelFormula(
        name="linear",
        expression="m * x",
        parameters=[ParameterSpec("m")],
        independent_vars=["x"],
    )
    mock_matlab = MagicMock()
    mock_engine_mod = MagicMock()
    mock_matlab.engine = mock_engine_mod
    mock_engine_mod.start_matlab.side_effect = RuntimeError("License server unreachable")
    with (
        patch("scimodel.adapters.matlab_solver.is_matlab_engine_installed", return_value=True),
        patch.dict("sys.modules", {"matlab": mock_matlab, "matlab.engine": mock_engine_mod}),
        pytest.raises(MatlabUnavailableError, match="Failed to initialize MATLAB engine"),
    ):
        solver.fit(formula, np.array([1.0, 2.0]), np.array([1.0, 2.0]))
