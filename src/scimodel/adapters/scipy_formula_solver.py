"""Generic mathematical formula solver using SciPy Trust Region Reflective least squares."""

from __future__ import annotations

import warnings
from collections.abc import Mapping, Sequence
from typing import cast

import numpy as np
import numpy.typing as npt
from scipy.optimize import least_squares
from scipy.stats import t

from scimodel.domain.fit import FitResult, ModelFitError
from scimodel.domain.formula import ModelFormula
from scimodel.domain.ports import ModelSolverPort


class ScipyFormulaSolver(ModelSolverPort):
    """Solver adapter that fits any valid ModelFormula using SciPy TRF.

    ``x`` may be a 1D array (single independent variable) or a mapping from
    each independent variable name to its array. Optional ``starts`` enable a
    multi-start search, ``loss`` enables robust fitting (e.g. ``"soft_l1"``),
    and ``jacobian_scaling`` rescales badly conditioned parameters.
    """

    def __init__(
        self,
        *,
        loss: str = "linear",
        jacobian_scaling: bool = False,
        max_evaluations: int | None = None,
    ) -> None:
        self.loss = loss
        self.jacobian_scaling = jacobian_scaling
        self.max_evaluations = max_evaluations

    @property
    def backend_name(self) -> str:
        return "scipy"

    def is_available(self) -> bool:
        return True

    def fit(
        self,
        formula: ModelFormula,
        x: npt.NDArray[np.float64] | Mapping[str, npt.NDArray[np.float64]],
        y: npt.NDArray[np.float64],
        *,
        starts: Sequence[Mapping[str, float]] = (),
    ) -> FitResult:
        variables = self._variables(formula, x)
        if y.ndim != 1 or any(
            values.ndim != 1 or values.shape != y.shape for values in variables.values()
        ):
            msg = "x and y data must be 1D arrays of matching length."
            raise ModelFitError(msg)

        num_params = len(formula.parameters)
        if len(y) <= num_params:
            msg = (
                f"At least {num_params + 1} observations are required "
                f"to fit {num_params} parameters."
            )
            raise ModelFitError(msg)

        if not np.all(np.isfinite(y)) or not all(
            np.all(np.isfinite(values)) for values in variables.values()
        ):
            msg = "Data contains non-finite values (NaN or Inf)."
            raise ModelFitError(msg)

        lb = np.array([p.lower_bound for p in formula.parameters], dtype=np.float64)
        ub = np.array([p.upper_bound for p in formula.parameters], dtype=np.float64)
        p0 = np.clip(self._default_start(formula), lb + 1e-8, ub - 1e-8)
        candidates = [p0]
        for start in starts:
            vector = np.array(
                [float(start.get(p.name, p0[i])) for i, p in enumerate(formula.parameters)],
                dtype=np.float64,
            )
            if np.all(np.isfinite(vector)):
                candidates.append(np.clip(vector, lb + 1e-8, ub - 1e-8))

        def residuals(params: npt.NDArray[np.float64]) -> npt.NDArray[np.float64]:
            param_map = {p.name: float(params[i]) for i, p in enumerate(formula.parameters)}
            try:
                pred = formula.evaluate(variables, param_map)
                res = np.broadcast_to(pred, y.shape) - y
                if not np.all(np.isfinite(res)):
                    return np.full_like(y, 1e12)
                return res
            except Exception:
                return np.full_like(y, 1e12)

        optimization = None
        best_start = p0
        last_error: Exception | None = None
        budget = self.max_evaluations or (200 * (num_params + 1) if starts else None)
        for start_vector in candidates:
            try:
                with np.errstate(all="ignore"), warnings.catch_warnings():
                    warnings.simplefilter("ignore", RuntimeWarning)
                    attempt = least_squares(
                        residuals,
                        start_vector,
                        bounds=(lb, ub),
                        method="trf",
                        ftol=1e-8,
                        xtol=1e-8,
                        gtol=1e-8,
                        loss=self.loss,
                        x_scale="jac" if self.jacobian_scaling else 1.0,
                        max_nfev=budget,
                    )
            except Exception as exc:
                last_error = exc
                continue
            if optimization is None or float(attempt.cost) < float(optimization.cost):
                optimization = attempt
                best_start = start_vector
        if optimization is None:
            msg = f"Formula optimization failed for '{formula.name}': {last_error}"
            raise ModelFitError(msg)

        fitted_params = cast(npt.NDArray[np.float64], optimization.x)
        param_dict = {p.name: float(fitted_params[i]) for i, p in enumerate(formula.parameters)}
        init_param_dict = {p.name: float(best_start[i]) for i, p in enumerate(formula.parameters)}

        # Evaluate final predictions
        fitted_y = np.broadcast_to(formula.evaluate(variables, param_dict), y.shape)
        errors = y - fitted_y
        rss = float(np.sum(errors**2))
        if not np.isfinite(rss) or rss >= 1e20:
            msg = f"Formula '{formula.name}' produced non-finite predictions at the optimum."
            raise ModelFitError(msg)
        rmse = float(np.sqrt(rss / len(y)))
        ss_tot = float(np.sum((y - np.mean(y)) ** 2))
        r_squared = 1.0 - (rss / ss_tot) if ss_tot > 0 else float("nan")

        # Standard errors & confidence intervals
        jacobian = cast(npt.NDArray[np.float64], optimization.jac)
        se_tuple = self._calc_standard_errors(jacobian, rss, len(y), num_params)
        ci_tuple = self._calc_confidence_intervals(fitted_params, se_tuple, len(y), num_params)

        se_dict = {p.name: se_tuple[i] for i, p in enumerate(formula.parameters)}
        ci_dict = {p.name: ci_tuple[i] for i, p in enumerate(formula.parameters)}

        return FitResult(
            model=formula.name,
            parameters=param_dict,
            standard_errors=se_dict,
            confidence_intervals=ci_dict,
            metrics={"rss": rss, "rmse": rmse, "r_squared": r_squared},
            initial_parameters=init_param_dict,
            converged=bool(optimization.success),
            function_evaluations=int(optimization.nfev),
            observations=len(y),
            parameter_correlation=self._correlation(formula, jacobian),
        )

    @staticmethod
    def _variables(
        formula: ModelFormula,
        x: npt.NDArray[np.float64] | Mapping[str, npt.NDArray[np.float64]],
    ) -> dict[str, npt.NDArray[np.float64]]:
        if isinstance(x, Mapping):
            missing = [name for name in formula.independent_vars if name not in x]
            if missing:
                msg = f"Missing data for independent variable(s): {', '.join(missing)}."
                raise ModelFitError(msg)
            return {
                name: np.asarray(x[name], dtype=np.float64) for name in formula.independent_vars
            }
        if len(formula.independent_vars) != 1:
            msg = "Formulas with several independent variables require a mapping of arrays."
            raise ModelFitError(msg)
        return {formula.independent_vars[0]: np.asarray(x, dtype=np.float64)}

    @staticmethod
    def _default_start(formula: ModelFormula) -> npt.NDArray[np.float64]:
        p0_list: list[float] = []
        for p in formula.parameters:
            if p.initial_guess is not None:
                p0_list.append(p.initial_guess)
            elif np.isfinite(p.lower_bound) and np.isfinite(p.upper_bound):
                p0_list.append((p.lower_bound + p.upper_bound) / 2.0)
            elif p.lower_bound > 0.0:
                p0_list.append(max(p.lower_bound * 1.5, 1.0))
            else:
                p0_list.append(1.0)
        return np.array(p0_list, dtype=np.float64)

    @staticmethod
    def _correlation(
        formula: ModelFormula, jacobian: npt.NDArray[np.float64]
    ) -> dict[str, dict[str, float]] | None:
        try:
            covariance = np.linalg.pinv(jacobian.T @ jacobian)
        except np.linalg.LinAlgError:
            return None
        scale = np.sqrt(np.clip(np.diag(covariance), 0.0, None))
        names = [p.name for p in formula.parameters]
        result: dict[str, dict[str, float]] = {}
        for i, first in enumerate(names):
            result[first] = {}
            for j, second in enumerate(names):
                denominator = scale[i] * scale[j]
                value = covariance[i, j] / denominator if denominator > 0 else float("nan")
                result[first][second] = float(np.clip(value, -1.0, 1.0))
        return result

    def _calc_standard_errors(
        self,
        jacobian: npt.NDArray[np.float64],
        rss: float,
        observations: int,
        parameters: int,
    ) -> tuple[float, ...]:
        degrees_of_freedom = observations - parameters
        if degrees_of_freedom <= 0:
            return tuple(float("nan") for _ in range(parameters))
        try:
            covariance = np.linalg.pinv(jacobian.T @ jacobian) * (rss / degrees_of_freedom)
            diagonal = np.clip(np.diag(covariance), 0.0, None)
            return tuple(float(val) for val in np.sqrt(diagonal))
        except np.linalg.LinAlgError:
            return tuple(float("nan") for _ in range(parameters))

    def _calc_confidence_intervals(
        self,
        parameters: npt.NDArray[np.float64],
        standard_errors: tuple[float, ...],
        observations: int,
        fitted_parameters: int,
    ) -> tuple[tuple[float, float], ...]:
        degrees_of_freedom = observations - fitted_parameters
        if degrees_of_freedom <= 0:
            return tuple((float("nan"), float("nan")) for _ in parameters)
        critical_value = float(t.ppf(0.975, degrees_of_freedom))
        return tuple(
            (float(p - critical_value * se), float(p + critical_value * se))
            for p, se in zip(parameters, standard_errors, strict=True)
        )
