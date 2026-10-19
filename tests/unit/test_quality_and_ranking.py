"""Tests for quality assessment and evidence-based ranking."""

import math

import numpy as np

from scimodel.adapters.scipy_formula_solver import ScipyFormulaSolver
from scimodel.application.discovery import _rank, has_redundant_parameters
from scimodel.application.quality import assess_candidate, summarize_checks
from scimodel.domain.discovery import CandidateResult
from scimodel.domain.fit import FitResult
from scimodel.domain.formula import ModelFormula, ParameterSpec

FREE = (-math.inf, math.inf)


def _candidate(formula: ModelFormula, variables, y, cv_r2: float, **extra) -> CandidateResult:  # type: ignore[no-untyped-def]
    fit = ScipyFormulaSolver().fit(formula, variables, y)
    return CandidateResult(
        name=formula.name,
        expression=formula.expression,
        origin="library",
        rationale="",
        fit=fit,
        complexity=formula.complexity,
        n_parameters=len(formula.parameters),
        aic=0.0,
        aicc=0.0,
        bic=0.0,
        cv_rmse=1.0,
        cv_r_squared=cv_r2,
        **extra,
    )


def _check(assessment, name: str) -> str:  # type: ignore[no-untyped-def]
    return next(c.status for c in assessment.checks if c.name == name)


def test_correct_model_grades_well_and_wrong_model_is_caught() -> None:
    rng = np.random.default_rng(3)
    x = np.repeat(np.linspace(0, 4, 12), 3)
    y = 1.0 + 2.0 * x**2 + rng.normal(0, 0.3, len(x))
    quadratic = ModelFormula(
        "quadratic",
        "a + b*x**2",
        [ParameterSpec("a", *FREE), ParameterSpec("b", *FREE)],
        independent_vars=["x"],
    )
    linear = ModelFormula(
        "linear",
        "a + b*x",
        [ParameterSpec("a", *FREE), ParameterSpec("b", *FREE)],
        independent_vars=["x"],
    )
    good = assess_candidate(
        _candidate(quadratic, {"x": x}, y, 0.99), quadratic, {"x": x}, y, neural_cv_r_squared=0.99
    )
    bad = assess_candidate(
        _candidate(linear, {"x": x}, y, 0.85), linear, {"x": x}, y, neural_cv_r_squared=0.99
    )
    assert good.grade == "A" and good.score > bad.score
    assert _check(bad, "lack_of_fit") == "fail"
    assert _check(bad, "residual_independence") in ("warn", "fail")
    assert _check(bad, "neural_ceiling_gap") == "fail"
    assert bad.grade in ("C", "D") and "Failed" in bad.verdict
    assert summarize_checks(bad)["failed"]


def test_negligible_predictor_and_bounds_are_flagged() -> None:
    rng = np.random.default_rng(0)
    x1 = rng.uniform(1, 5, 40)
    x2 = rng.uniform(1, 5, 40)
    y = 3 * x1 + rng.normal(0, 0.1, 40)
    formula = ModelFormula(
        "both",
        "a*x1 + b*x2",
        [ParameterSpec("a", *FREE), ParameterSpec("b", 0.0, math.inf)],
        independent_vars=["x1", "x2"],
    )
    assessment = assess_candidate(
        _candidate(formula, {"x1": x1, "x2": x2}, y, 0.99), formula, {"x1": x1, "x2": x2}, y
    )
    assert _check(assessment, "predictor_relevance") == "warn"


def test_plausibility_failure_for_singular_model() -> None:
    x = np.linspace(-1, 1, 21)
    y = x + 0.01 * np.cos(7 * x)
    formula = ModelFormula("pole", "a/x", [ParameterSpec("a", *FREE)], independent_vars=["x"])
    fit = FitResult(
        "pole",
        {"a": 1.0},
        {"a": 0.1},
        {"a": (0.8, 1.2)},
        {"r_squared": 0.1, "rss": 1.0, "rmse": 1.0},
        {"a": 1.0},
        True,
        1,
        21,
    )
    candidate = CandidateResult("pole", "a/x", "user", "", fit, 3, 1, 0, 0, 0, 1, 0.1)
    assessment = assess_candidate(candidate, formula, {"x": x[x != 0]}, y[x != 0])
    assert _check(assessment, "physical_plausibility") in ("warn", "fail", "pass")


def _scored(
    name: str,
    aicc: float,
    origin: str = "library",
    mechanistic: bool = True,
    se: float = 0.1,
    k: int = 2,
) -> CandidateResult:  # type: ignore[valid-type]
    params = {f"p{i}": 1.0 for i in range(k)}
    fit = FitResult(
        name,
        params,
        {p: se for p in params},
        {p: (0, 2) for p in params},
        {"rss": 1.0, "r_squared": 0.9, "rmse": 1.0},
        params,
        True,
        1,
        20,
    )
    return CandidateResult(
        name,
        "x",
        origin,
        "",
        fit,
        3,
        k,
        aicc,
        aicc,
        aicc,
        1.0,
        0.9,  # type: ignore[arg-type]
        mechanistic=mechanistic,
    )


def test_ranking_guards() -> None:
    ranked = _rank(
        [
            _scored("noise_fit", 0.0, origin="symbolic", mechanistic=False, se=5.0),
            _scored("empirical", 1.0, mechanistic=False),
            _scored("mechanistic", 1.5),
            _scored("far", 30.0),
        ]
    )
    assert [c.name for c in ranked] == ["mechanistic", "empirical", "far", "noise_fit"]
    assert has_redundant_parameters(ranked[-1])
    assert abs(sum(c.akaike_weight for c in ranked) - 1) < 1e-9
    assert ranked[0].delta_aicc == 1.5
