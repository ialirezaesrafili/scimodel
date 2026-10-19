"""Tests for the symbolic, sparse, and neural discovery engines and the extended solver."""

import numpy as np
import pytest

from scimodel.adapters.neural_surrogate import NeuralBaseline, NeuralSettings
from scimodel.adapters.scipy_formula_solver import ScipyFormulaSolver
from scimodel.adapters.sparse_regression import SparseRegressor, build_library
from scimodel.adapters.symbolic_regression import SymbolicRegressor, SymbolicSearchSettings
from scimodel.domain.fit import ModelFitError
from scimodel.domain.formula import ModelFormula, ParameterSpec

KEPLER_A = np.array([0.387, 0.723, 1.0, 1.524, 5.203, 9.537, 19.191, 30.069])
KEPLER_T = np.array([0.241, 0.615, 1.0, 1.881, 11.862, 29.457, 84.011, 164.79])


def test_symbolic_regression_rediscovers_keplers_third_law() -> None:
    regressor = SymbolicRegressor(SymbolicSearchSettings(seed=0, time_budget=10))
    proposals = regressor.propose({"a": KEPLER_A}, KEPLER_T, target="T")
    assert regressor.front[0].nrmse < 1e-3
    best = proposals[0]
    assert best.origin == "symbolic" and best.search_space > 100
    fit = ScipyFormulaSolver().fit(best.formula, {"a": KEPLER_A}, KEPLER_T, starts=best.starts)
    assert fit.metrics["r_squared"] > 0.99999
    # The discovered body must behave like a**1.5 across the data range.
    grid = np.linspace(0.4, 30, 20)
    predicted = best.formula.evaluate({"a": grid}, fit.parameters)
    assert np.allclose(predicted, grid**1.5, rtol=0.02)


def test_symbolic_regression_handles_degenerate_targets_and_name_clashes() -> None:
    assert SymbolicRegressor().propose({"x": np.arange(10.0)}, np.ones(10)) == []
    x = np.linspace(1, 5, 30)
    proposals = SymbolicRegressor(SymbolicSearchSettings(time_budget=3)).propose(
        {"a": x, "b": x[::-1]}, 2 * x + 1
    )
    for proposal in proposals:
        names = {p.name for p in proposal.formula.parameters}
        assert not names & {"a", "b"}


def test_sparse_regression_finds_arrhenius_power_law_structure() -> None:
    rng = np.random.default_rng(1)
    temperature = np.repeat(np.linspace(300, 380, 8), 4)
    loading = np.tile([0.5, 1.0, 2.0, 4.0], 8)
    rate = 1e7 * np.exp(-6000 / temperature) * loading**0.8 * rng.lognormal(0, 0.02, 32)
    proposals = SparseRegressor().propose(
        {"temperature": temperature, "loading": loading}, rate, target="rate"
    )
    expressions = [p.formula.expression for p in proposals]
    target = next(e for e in expressions if "1/temperature" in e and "log(loading)" in e)
    assert target.startswith("exp(")
    proposal = proposals[expressions.index(target)]
    fit = ScipyFormulaSolver().fit(
        proposal.formula,
        {"temperature": temperature, "loading": loading},
        rate,
        starts=proposal.starts,
    )
    slopes = {name: value for name, value in fit.parameters.items() if name != "w0"}
    assert any(abs(v + 6000) < 300 for v in slopes.values())
    assert any(abs(v - 0.8) < 0.05 for v in slopes.values())


def test_feature_library_respects_domains() -> None:
    names = [t.expression for t in build_library({"x": np.array([-1.0, 0.0, 2.0])})]
    assert "log(x)" not in names and "(1/x)" not in names and "sqrt(x)" not in names
    names = [t.expression for t in build_library({"x": np.array([1.0, 2.0, 3.0])})]
    assert {"log(x)", "(1/x)", "sqrt(x)"} <= set(names)


def test_neural_baseline_measures_learnable_signal() -> None:
    rng = np.random.default_rng(0)
    x = np.linspace(-2, 2, 80)
    y = np.tanh(2 * x) + rng.normal(0, 0.05, 80)
    report = NeuralBaseline(NeuralSettings(ensemble=1, max_epochs=800)).evaluate({"x": x}, y)
    assert report["status"] == "ok" and report["cv_r_squared"] > 0.95
    small = NeuralBaseline().evaluate({"x": x[:5]}, y[:5])
    assert small["status"] == "skipped"
    timed = NeuralBaseline(NeuralSettings(time_budget=0.0)).evaluate({"x": x}, y)
    assert timed["status"] == "skipped"


def test_multivariable_multistart_and_robust_solver() -> None:
    x1, x2 = np.meshgrid(np.linspace(1, 3, 6), np.linspace(1, 2, 5))
    x1, x2 = x1.ravel(), x2.ravel()
    y = 2.0 * x1**1.5 / x2
    formula = ModelFormula(
        "f",
        "A * x1**k / x2",
        [ParameterSpec("A", -np.inf, np.inf), ParameterSpec("k", -np.inf, np.inf)],
        independent_vars=["x1", "x2"],
    )
    fit = ScipyFormulaSolver(jacobian_scaling=True).fit(
        formula, {"x1": x1, "x2": x2}, y, starts=({"A": 5.0, "k": 0.5}, {"A": float("nan")})
    )
    assert abs(fit.parameters["k"] - 1.5) < 1e-6
    assert fit.parameter_correlation is not None and fit.parameter_correlation["A"]["A"] == 1.0
    robust = ScipyFormulaSolver(loss="soft_l1").fit(formula, {"x1": x1, "x2": x2}, y)
    assert abs(robust.parameters["A"] - 2.0) < 1e-4
    with pytest.raises(ModelFitError, match="mapping"):
        ScipyFormulaSolver().fit(formula, x1, y)
    with pytest.raises(ModelFitError, match="Missing data"):
        ScipyFormulaSolver().fit(formula, {"x1": x1}, y)


def test_formula_constants_and_complexity() -> None:
    formula = ModelFormula(
        "wave",
        "A*sin(2*pi*f*t)",
        [ParameterSpec("A", -1, 1), ParameterSpec("f", 0, 10)],
        independent_vars=["t"],
    )
    assert formula.complexity == 11
    value = formula.evaluate({"t": np.array([0.25])}, {"A": 1.0, "f": 1.0})
    assert np.allclose(value, 1.0)
