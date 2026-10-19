"""Unit tests for extensible ModelFormula and safe AST evaluation."""

import numpy as np
import pytest

from scimodel.domain.formula import (
    FormulaEvaluationError,
    FormulaSyntaxError,
    ModelFormula,
    ParameterSpec,
)


def test_michaelis_menten_formula_evaluation() -> None:
    """Verify safe evaluation of Michaelis-Menten formula on NumPy arrays."""
    formula = ModelFormula(
        name="michaelis_menten",
        expression="(Vmax * s) / (Km + s)",
        parameters=[
            ParameterSpec("Vmax", lower_bound=0.0),
            ParameterSpec("Km", lower_bound=0.0),
        ],
        independent_vars=["s"],
        dependent_var="v",
    )

    s_data = np.array([0.02, 0.05, 0.10, 0.50], dtype=np.float64)
    v_pred = formula.evaluate(
        variable_values={"s": s_data},
        parameter_values={"Vmax": 200.0, "Km": 0.05},
    )

    expected = (200.0 * s_data) / (0.05 + s_data)
    np.testing.assert_allclose(v_pred, expected, rtol=1e-7)


def test_hill_equation_formula_evaluation() -> None:
    """Verify evaluation of multi-parameter Hill equation with exponents."""
    formula = ModelFormula(
        name="hill_kinetics",
        expression="(Vmax * (s ** n)) / ((Khalf ** n) + (s ** n))",
        parameters=[
            ParameterSpec("Vmax", lower_bound=0.0),
            ParameterSpec("Khalf", lower_bound=0.0),
            ParameterSpec("n", lower_bound=0.5, upper_bound=4.0),
        ],
        independent_vars=["s"],
    )

    s_data = np.array([0.1, 0.5, 1.0, 2.0], dtype=np.float64)
    v_pred = formula.evaluate(
        variable_values={"s": s_data},
        parameter_values={"Vmax": 150.0, "Khalf": 0.5, "n": 2.0},
    )

    expected = (150.0 * (s_data**2.0)) / ((0.5**2.0) + (s_data**2.0))
    np.testing.assert_allclose(v_pred, expected, rtol=1e-7)


def test_whitelisted_math_functions() -> None:
    """Verify exponential decay with exp() function call."""
    formula = ModelFormula(
        name="first_order_decay",
        expression="C0 * exp(-k * t)",
        parameters=[
            ParameterSpec("C0", lower_bound=0.0),
            ParameterSpec("k", lower_bound=0.0),
        ],
        independent_vars=["t"],
    )

    t_data = np.array([0.0, 1.0, 2.0, 5.0], dtype=np.float64)
    c_pred = formula.evaluate(
        variable_values={"t": t_data},
        parameter_values={"C0": 100.0, "k": 0.5},
    )
    expected = 100.0 * np.exp(-0.5 * t_data)
    np.testing.assert_allclose(c_pred, expected, rtol=1e-7)


def test_reject_code_injection_and_unsafe_expressions() -> None:
    """Prohibit arbitrary code execution or forbidden functions in formula expressions."""
    # Forbidden function call
    with pytest.raises(
        FormulaSyntaxError, match=r"Unsupported AST syntax node|Undefined or forbidden symbol"
    ):
        ModelFormula(
            name="malicious",
            expression="__import__('os').system('ls')",
            parameters=[ParameterSpec("x")],
            independent_vars=["s"],
        )

    # Undefined parameter
    with pytest.raises(FormulaSyntaxError, match="Undefined or forbidden symbol 'unregistered'"):
        ModelFormula(
            name="missing_param",
            expression="registered * s + unregistered",
            parameters=[ParameterSpec("registered")],
            independent_vars=["s"],
        )


def test_parameter_spec_invariants() -> None:
    """Verify ParameterSpec bounds and identifier checks."""
    with pytest.raises(ValueError, match="not a valid identifier"):
        ParameterSpec("123invalid")

    with pytest.raises(ValueError, match="strictly less than upper_bound"):
        ParameterSpec("k", lower_bound=10.0, upper_bound=5.0)


def test_evaluation_missing_variable_error() -> None:
    """Raise FormulaEvaluationError when required variable values are omitted."""
    formula = ModelFormula(
        name="linear",
        expression="m * x + b",
        parameters=[ParameterSpec("m"), ParameterSpec("b")],
        independent_vars=["x"],
    )

    with pytest.raises(FormulaEvaluationError, match="Missing value for independent variable 'x'"):
        formula.evaluate(
            variable_values={},
            parameter_values={"m": 1.0, "b": 0.0},
        )
