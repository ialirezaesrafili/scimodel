"""SciPy implementation of the Michaelis–Menten solver port."""

from __future__ import annotations

import numpy as np
from scipy.optimize import least_squares
from scipy.stats import t

from scimodel.domain.fit import FitResult, ModelFitError
from scimodel.domain.kinetics import michaelis_menten


def fit_michaelis_menten(
    substrate: np.ndarray,
    velocity: np.ndarray,
) -> FitResult:
    """Fit Michaelis–Menten parameters with bounded TRF least squares."""
    if substrate.ndim != 1 or velocity.ndim != 1 or substrate.shape != velocity.shape:
        raise ModelFitError(
            "Substrate and velocity arrays must be one-dimensional and equal in length."
        )
    if len(substrate) < 4:
        raise ModelFitError("At least 4 observations are required for model fitting.")
    if not np.isfinite(substrate).all() or not np.isfinite(velocity).all():
        raise ModelFitError("Model inputs must contain only finite values.")
    if (substrate < 0).any() or (velocity < 0).any():
        raise ModelFitError("Model inputs cannot contain negative values.")
    if len(np.unique(substrate)) < 4:
        raise ModelFitError("At least 4 distinct substrate concentration levels are required.")

    initial = _lineweaver_burk_initial_guess(substrate, velocity)

    def residuals(parameters: np.ndarray) -> np.ndarray:
        return michaelis_menten(substrate, parameters[0], parameters[1]) - velocity

    try:
        optimization = least_squares(
            residuals,
            x0=initial,
            bounds=(np.zeros(2), np.full(2, np.inf)),
            method="trf",
            x_scale="jac",
        )
    except (ValueError, np.linalg.LinAlgError) as exc:
        raise ModelFitError(f"Michaelis–Menten optimization failed: {exc}") from exc

    parameters = optimization.x
    fitted = michaelis_menten(substrate, parameters[0], parameters[1])
    errors = velocity - fitted
    rss = float(np.sum(errors**2))
    rmse = float(np.sqrt(rss / len(velocity)))
    total_sum_squares = float(np.sum((velocity - np.mean(velocity)) ** 2))
    r_squared = 1.0 - (rss / total_sum_squares) if total_sum_squares else float("nan")
    standard_errors = _standard_errors(optimization.jac, rss, len(velocity), len(parameters))
    confidence_intervals = _confidence_intervals(
        parameters,
        standard_errors,
        observations=len(velocity),
        fitted_parameters=len(parameters),
    )

    return FitResult(
        model="michaelis_menten",
        parameters={"vmax": float(parameters[0]), "km": float(parameters[1])},
        standard_errors={"vmax": standard_errors[0], "km": standard_errors[1]},
        confidence_intervals={
            "vmax": confidence_intervals[0],
            "km": confidence_intervals[1],
        },
        metrics={"rss": rss, "rmse": rmse, "r_squared": r_squared},
        initial_parameters={"vmax": float(initial[0]), "km": float(initial[1])},
        converged=bool(optimization.success),
        function_evaluations=int(optimization.nfev),
        observations=len(velocity),
    )


def _lineweaver_burk_initial_guess(
    substrate: np.ndarray,
    velocity: np.ndarray,
) -> np.ndarray:
    """Get positive seeds from reciprocal coordinates when possible."""
    positive = (substrate > 0) & (velocity > 0)
    if positive.sum() >= 2:
        slope, intercept = np.polyfit(1.0 / substrate[positive], 1.0 / velocity[positive], 1)
        if intercept > 0 and slope > 0 and np.isfinite(slope + intercept):
            return np.array([1.0 / intercept, slope / intercept], dtype=float)

    vmax_guess = max(float(np.max(velocity)), np.finfo(float).eps)
    km_guess = max(float(np.median(substrate[substrate > 0])), np.finfo(float).eps)
    return np.array([vmax_guess, km_guess], dtype=float)


def _standard_errors(
    jacobian: np.ndarray,
    rss: float,
    observations: int,
    parameters: int,
) -> tuple[float, ...]:
    """Estimate parameter standard errors from the least-squares Jacobian."""
    degrees_of_freedom = observations - parameters
    if degrees_of_freedom <= 0:
        raise ModelFitError("Not enough residual degrees of freedom for uncertainty estimates.")
    covariance = np.linalg.pinv(jacobian.T @ jacobian) * (rss / degrees_of_freedom)
    diagonal = np.clip(np.diag(covariance), 0.0, None)
    return tuple(float(value) for value in np.sqrt(diagonal))


def _confidence_intervals(
    parameters: np.ndarray,
    standard_errors: tuple[float, ...],
    *,
    observations: int,
    fitted_parameters: int,
) -> tuple[tuple[float, float], ...]:
    """Calculate studentized 95% confidence intervals."""
    degrees_of_freedom = observations - fitted_parameters
    critical_value = float(t.ppf(0.975, degrees_of_freedom))
    return tuple(
        (float(value - critical_value * error), float(value + critical_value * error))
        for value, error in zip(parameters, standard_errors, strict=True)
    )
