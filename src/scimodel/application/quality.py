"""Model-agnostic quality assessment of a fitted formula.

Checks cover optimizer convergence, explained variance, generalization
(cross-validation), residual structure (normality, constant variance,
independence), parameter identifiability, lack of fit against replicate
pure error, outlier sensitivity, physical plausibility, and the gap to a
neural-network ceiling. Every check has a technical message and a
plain-language explanation so that reports work for all expertise levels.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any, TypeAlias

import numpy as np
import numpy.typing as npt

from scimodel.adapters.scipy_formula_solver import ScipyFormulaSolver
from scimodel.adapters.scipy_statistics import (
    durbin_watson,
    f_test_p_value,
    runs_test_p_value,
    shapiro_p_value,
    spearman,
)
from scimodel.domain.discovery import CandidateResult, CheckStatus, QualityAssessment, QualityCheck
from scimodel.domain.fit import ModelFitError
from scimodel.domain.formula import FormulaEvaluationError, ModelFormula

FloatArray: TypeAlias = npt.NDArray[np.float64]

_WEIGHTS: Mapping[str, float] = {
    "convergence": 3.0,
    "explained_variance": 2.0,
    "generalization": 2.5,
    "residual_independence": 2.5,
    "lack_of_fit": 2.5,
    "parameter_identifiability": 2.0,
    "parameter_correlation": 1.0,
    "residual_normality": 1.0,
    "constant_variance": 1.0,
    "outlier_sensitivity": 1.5,
    "physical_plausibility": 1.5,
    "neural_ceiling_gap": 1.5,
    "parameters_at_bounds": 1.0,
}


def assess_candidate(
    candidate: CandidateResult,
    formula: ModelFormula,
    variables: dict[str, FloatArray],
    y: FloatArray,
    *,
    neural_cv_r_squared: float | None = None,
) -> QualityAssessment:
    """Run every applicable check and aggregate a score, grade, and verdict."""
    fit = candidate.fit
    predicted = np.broadcast_to(formula.evaluate(variables, fit.parameters), y.shape)
    residuals = y - predicted
    n, k = len(y), candidate.n_parameters
    checks: list[QualityCheck] = []

    checks.append(
        QualityCheck(
            "convergence",
            "pass" if fit.converged else "fail",
            "Optimizer converged." if fit.converged else "Optimizer did not converge.",
            "The fitting algorithm found a stable best solution."
            if fit.converged
            else "The fitting algorithm did not settle; parameter values are unreliable.",
            fit.converged,
        )
    )

    r2 = float(fit.metrics.get("r_squared", float("nan")))
    adjusted = 1 - (1 - r2) * (n - 1) / (n - k - 1) if n - k - 1 > 0 else float("nan")
    status: CheckStatus = "pass" if adjusted >= 0.9 else "warn" if adjusted >= 0.6 else "fail"
    checks.append(
        QualityCheck(
            "explained_variance",
            status,
            f"R² = {r2:.4f}, adjusted R² = {adjusted:.4f}.",
            f"The model explains about {max(r2, 0) * 100:.0f}% of the variation in the data.",
            round(adjusted, 6) if math.isfinite(adjusted) else None,
        )
    )

    gap = r2 - candidate.cv_r_squared
    if math.isfinite(candidate.cv_r_squared):
        status = "pass" if gap < 0.05 else "warn" if gap < 0.2 else "fail"
        checks.append(
            QualityCheck(
                "generalization",
                status,
                f"Cross-validated R² = {candidate.cv_r_squared:.4f} (gap {gap:.3f} to in-sample).",
                "Predictions on held-out data are about as good as on fitted data."
                if status == "pass"
                else "The model does noticeably worse on data it has not seen; it may be "
                "overfitting noise.",
                round(candidate.cv_r_squared, 6),
            )
        )
    else:
        checks.append(_skip("generalization", "Cross-validation was not possible."))

    order = np.lexsort([variables[name] for name in reversed(list(variables))])
    ordered = residuals[order]
    runs_p = runs_test_p_value(ordered)
    dw = durbin_watson(ordered)
    if runs_p is None:
        checks.append(_skip("residual_independence", "Too few residuals for a runs test."))
    else:
        status = "pass" if runs_p >= 0.05 else "warn" if runs_p >= 0.01 else "fail"
        checks.append(
            QualityCheck(
                "residual_independence",
                status,
                f"Runs test p = {runs_p:.3g}; Durbin–Watson = {dw:.2f}."
                if dw is not None
                else f"Runs test p = {runs_p:.3g}.",
                "Errors look randomly scattered around the curve."
                if status == "pass"
                else "Errors form systematic runs above and below the curve: the equation "
                "probably misses part of the true shape.",
                round(runs_p, 6),
            )
        )

    checks.append(_lack_of_fit(variables, y, residuals, k))

    se_ratio: list[float] = []
    for name, value in fit.parameters.items():
        error = fit.standard_errors.get(name, float("nan"))
        if math.isfinite(error) and value != 0:
            se_ratio.append(abs(error / value))
        else:
            se_ratio.append(float("inf"))
    worst = max(se_ratio) if se_ratio else 0.0
    status = "pass" if worst < 0.25 else "warn" if worst < 1.0 else "fail"
    checks.append(
        QualityCheck(
            "parameter_identifiability",
            status,
            f"Largest relative standard error = {worst:.3g}.",
            "Every parameter is pinned down precisely by the data."
            if status == "pass"
            else "At least one parameter is poorly determined; the data cannot tell its value "
            "apart from zero or from other values.",
            round(worst, 6) if math.isfinite(worst) else "inf",
        )
    )

    correlation = fit.parameter_correlation or {}
    max_corr = max(
        (
            abs(value)
            for first, row in correlation.items()
            for second, value in row.items()
            if first < second and math.isfinite(value)
        ),
        default=0.0,
    )
    if len(fit.parameters) > 1:
        status = "pass" if max_corr < 0.95 else "warn" if max_corr < 0.995 else "fail"
        checks.append(
            QualityCheck(
                "parameter_correlation",
                status,
                f"Maximum |parameter correlation| = {max_corr:.4f}.",
                "Parameters are estimated independently enough to interpret separately."
                if status == "pass"
                else "Some parameters trade off against each other; consider a "
                "reparametrization or data covering a wider range.",
                round(max_corr, 6),
            )
        )

    normal_p = shapiro_p_value(residuals)
    if normal_p is None:
        checks.append(_skip("residual_normality", "Too few residuals for Shapiro–Wilk."))
    else:
        status = "pass" if normal_p >= 0.05 else "warn"
        checks.append(
            QualityCheck(
                "residual_normality",
                status,
                f"Shapiro–Wilk p = {normal_p:.3g}.",
                "Errors are consistent with normal measurement noise, so confidence intervals "
                "are trustworthy."
                if status == "pass"
                else "Errors are not normally distributed; confidence intervals may be "
                "approximate.",
                round(normal_p, 6),
            )
        )

    rho, rho_p = spearman(predicted.astype(np.float64), np.abs(residuals))
    if n >= 8:
        status = "pass" if rho_p >= 0.05 or abs(rho) < 0.3 else "warn"
        checks.append(
            QualityCheck(
                "constant_variance",
                status,
                f"Spearman ρ(|residual|, fitted) = {rho:.3f} (p = {rho_p:.3g}).",
                "Scatter is similar across the whole range."
                if status == "pass"
                else "Scatter grows or shrinks with the response; a weighted fit or a "
                "log-scale model may be more appropriate.",
                round(rho, 6),
            )
        )

    if len(variables) > 1:
        checks.append(_predictor_relevance(formula, fit.parameters, variables, y))
    checks.append(_outlier_sensitivity(formula, fit.parameters, variables, y, residuals, k))
    checks.append(_plausibility(formula, fit.parameters, variables, y))

    at_bounds = [
        spec.name
        for spec in formula.parameters
        if any(
            math.isfinite(bound)
            and abs(fit.parameters[spec.name] - bound) <= 1e-6 * max(1.0, abs(bound))
            for bound in (spec.lower_bound, spec.upper_bound)
        )
    ]
    checks.append(
        QualityCheck(
            "parameters_at_bounds",
            "warn" if at_bounds else "pass",
            f"Parameters at a bound: {', '.join(at_bounds)}."
            if at_bounds
            else "No parameter is at a bound.",
            "A parameter hit its allowed limit, so the model may be the wrong shape."
            if at_bounds
            else "All parameters settled inside their allowed ranges.",
            len(at_bounds),
        )
    )

    if neural_cv_r_squared is not None and math.isfinite(candidate.cv_r_squared):
        ceiling_gap = neural_cv_r_squared - candidate.cv_r_squared
        status = "pass" if ceiling_gap < 0.03 else "warn" if ceiling_gap < 0.1 else "fail"
        checks.append(
            QualityCheck(
                "neural_ceiling_gap",
                status,
                f"Neural network CV R² = {neural_cv_r_squared:.4f}; gap = {ceiling_gap:.4f}.",
                "A flexible neural network cannot predict better than this equation, so the "
                "equation captures the learnable structure."
                if status == "pass"
                else "A flexible neural network predicts better: there is structure the "
                "equation does not capture yet.",
                round(ceiling_gap, 6),
            )
        )

    score = _score(checks)
    grade = "A" if score >= 85 else "B" if score >= 70 else "C" if score >= 50 else "D"
    return QualityAssessment(
        candidate.name, tuple(checks), round(score, 1), grade, _verdict(grade, checks)
    )


def _skip(name: str, message: str) -> QualityCheck:
    return QualityCheck(name, "skip", message, message)


def _lack_of_fit(
    variables: dict[str, FloatArray], y: FloatArray, residuals: FloatArray, k: int
) -> QualityCheck:
    keys = np.column_stack(list(variables.values()))
    _, inverse, counts = np.unique(keys, axis=0, return_inverse=True, return_counts=True)
    inverse = inverse.reshape(-1)
    groups = len(counts)
    n = len(y)
    if groups == n or groups <= k:
        return _skip("lack_of_fit", "No replicated predictor settings for a pure-error test.")
    group_means = np.bincount(inverse, weights=y) / counts
    pure_error = float(np.sum((y - group_means[inverse]) ** 2))
    total = float(np.sum(residuals**2))
    lack = max(total - pure_error, 0.0)
    df_lack, df_pure = groups - k, n - groups
    if pure_error <= 0 or df_lack <= 0 or df_pure <= 0:
        return _skip("lack_of_fit", "Replicates have no spread; pure error is zero.")
    f_stat = (lack / df_lack) / (pure_error / df_pure)
    p_value = f_test_p_value(f_stat, df_lack, df_pure)
    status: CheckStatus = "pass" if p_value >= 0.05 else "warn" if p_value >= 0.01 else "fail"
    return QualityCheck(
        "lack_of_fit",
        status,
        f"Lack-of-fit F = {f_stat:.3g} (df {df_lack}, {df_pure}), p = {p_value:.3g}.",
        "Deviations from the curve are no larger than the scatter between repeated measurements."
        if status == "pass"
        else "The curve misses the replicate averages by more than measurement noise explains.",
        round(p_value, 6),
    )


def _outlier_sensitivity(
    formula: ModelFormula,
    parameters: dict[str, float],
    variables: dict[str, FloatArray],
    y: FloatArray,
    residuals: FloatArray,
    k: int,
) -> QualityCheck:
    n = len(y)
    scale = math.sqrt(float(np.sum(residuals**2)) / max(n - k, 1))
    extreme = int(np.sum(np.abs(residuals) > 3 * scale)) if scale > 0 else 0
    try:
        robust = ScipyFormulaSolver(loss="soft_l1").fit(formula, variables, y, starts=(parameters,))
    except (ModelFitError, FormulaEvaluationError):
        return _skip("outlier_sensitivity", "Robust refit was not possible.")
    changes = [
        abs(robust.parameters[name] - value) / max(abs(value), 1e-12)
        for name, value in parameters.items()
    ]
    worst = max(changes, default=0.0)
    status: CheckStatus = (
        "pass" if worst < 0.1 and extreme == 0 else "warn" if worst < 0.3 else "fail"
    )
    return QualityCheck(
        "outlier_sensitivity",
        status,
        f"{extreme} residual(s) beyond 3σ; robust refit changes parameters by up to "
        f"{worst * 100:.1f}%.",
        "No single point drives the result."
        if status == "pass"
        else "A few unusual points noticeably change the result; check them for measurement "
        "errors.",
        round(worst, 6),
    )


def _plausibility(
    formula: ModelFormula,
    parameters: dict[str, float],
    variables: dict[str, FloatArray],
    y: FloatArray,
) -> QualityCheck:
    grid = {
        name: np.linspace(float(values.min()), float(values.max()), 200)
        for name, values in variables.items()
    }
    try:
        curve = np.broadcast_to(formula.evaluate(grid, parameters), (200,))
    except FormulaEvaluationError:
        return QualityCheck(
            "physical_plausibility",
            "fail",
            "The model cannot be evaluated across the observed range.",
            "The equation breaks down (division by zero or similar) inside the data range.",
        )
    if not np.all(np.isfinite(curve)):
        return QualityCheck(
            "physical_plausibility",
            "fail",
            "Non-finite predictions inside the observed range.",
            "The equation produces impossible values between the measured points.",
        )
    if np.all(y >= 0) and np.any(curve < -0.05 * float(np.ptp(y))):
        return QualityCheck(
            "physical_plausibility",
            "warn",
            "Predictions become negative although every observation is non-negative.",
            "Between the data points the equation predicts negative values, which may be "
            "physically impossible.",
        )
    span = float(np.ptp(y)) or 1.0
    if (
        float(np.max(curve)) > float(np.max(y)) + 2 * span
        or float(np.min(curve)) < float(np.min(y)) - 2 * span
    ):
        return QualityCheck(
            "physical_plausibility",
            "warn",
            "Predictions swing far outside the observed response range between data points.",
            "The equation wiggles wildly between the measurements; it may be overfitted.",
        )
    return QualityCheck(
        "physical_plausibility",
        "pass",
        "Predictions stay finite and within a plausible range across the data.",
        "The curve behaves sensibly between the measured points.",
    )


def _predictor_relevance(
    formula: ModelFormula,
    parameters: dict[str, float],
    variables: dict[str, FloatArray],
    y: FloatArray,
) -> QualityCheck:
    """Flag predictors whose effect on predictions is practically negligible."""
    span = float(np.ptp(y)) or 1.0
    medians = {name: np.full(50, float(np.median(values))) for name, values in variables.items()}
    negligible: list[str] = []
    effects: dict[str, float] = {}
    for name, values in variables.items():
        grid = dict(medians)
        grid[name] = np.linspace(float(values.min()), float(values.max()), 50)
        try:
            curve = np.broadcast_to(formula.evaluate(grid, parameters), (50,))
        except FormulaEvaluationError:
            continue
        if not np.all(np.isfinite(curve)):
            continue
        effects[name] = float(np.ptp(curve)) / span
        if effects[name] < 0.01:
            negligible.append(name)
    summary = ", ".join(f"{name}: {effect * 100:.2f}%" for name, effect in effects.items())
    return QualityCheck(
        "predictor_relevance",
        "warn" if negligible else "pass",
        f"Effect of each predictor as % of the response range — {summary}.",
        f"{', '.join(negligible)} change(s) the prediction by less than 1% of the observed "
        "range; a simpler model without them may be preferable."
        if negligible
        else "Every predictor has a practically relevant effect on the prediction.",
        ", ".join(negligible) or None,
    )


def _score(checks: list[QualityCheck]) -> float:
    values = {"pass": 1.0, "warn": 0.5, "fail": 0.0}
    total = weight = 0.0
    for check in checks:
        if check.status == "skip":
            continue
        w = _WEIGHTS.get(check.name, 1.0)
        total += w * values[check.status]
        weight += w
    return 100.0 * total / weight if weight else 0.0


def _verdict(grade: str, checks: list[QualityCheck]) -> str:
    failed = [check.name.replace("_", " ") for check in checks if check.status == "fail"]
    warned = [check.name.replace("_", " ") for check in checks if check.status == "warn"]
    if grade == "A":
        text = "Strong candidate: the fit is accurate, generalizes, and shows no structural misfit."
    elif grade == "B":
        text = "Good candidate with minor concerns worth reviewing."
    elif grade == "C":
        text = "Usable only with caution; important diagnostics raise concerns."
    else:
        text = "Not reliable for scientific interpretation in its current form."
    if failed:
        text += f" Failed: {', '.join(failed)}."
    if warned:
        text += f" Review: {', '.join(warned)}."
    return text


def summarize_checks(assessment: QualityAssessment) -> dict[str, Any]:
    return {
        "grade": assessment.grade,
        "score": assessment.score,
        "failed": [c.name for c in assessment.checks if c.status == "fail"],
        "warnings": [c.name for c in assessment.checks if c.status == "warn"],
    }
