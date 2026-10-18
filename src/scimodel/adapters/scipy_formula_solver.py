"""Generic mathematical formula solver using SciPy Trust Region Reflective least squares."""

from __future__ import annotations

from typing import cast

import numpy as np
import numpy.typing as npt
from scipy.optimize import least_squares
from scipy.stats import t

from scimodel.domain.fit import FitResult, ModelFitError
from scimodel.domain.formula import ModelFormula
from scimodel.domain.ports import ModelSolverPort


class ScipyFormulaSolver(ModelSolverPort):
    """Solver adapter that fits any valid ModelFormula using SciPy TRF."""

    @property
    def backend_name(self) -> str:
        return "scipy"

    def is_available(self) -> bool:
        return True

    def fit(
        self,
        formula: ModelFormula,
        x: npt.NDArray[np.float64],
        y: npt.NDArray[np.float64],
    ) -> FitResult:
        if x.ndim != 1 or y.ndim != 1 or x.shape != y.shape:
            msg = "x and y data must be 1D arrays of matching length."
            raise ModelFitError(msg)

        num_params = len(formula.parameters)
        if len(x) <= num_params:
            msg = (
                f"At least {num_params + 1} observations are required "
                f"to fit {num_params} parameters."
            )
            raise ModelFitError(msg)

        if not np.all(np.isfinite(x)) or not np.all(np.isfinite(y)):
            msg = "Data contains non-finite values (NaN or Inf)."
            raise ModelFitError(msg)

        # Build initial guesses and bounds
        p0_list: list[float] = []
        lb_list: list[float] = []
        ub_list: list[float] = []

        for p in formula.parameters:
            lb_list.append(p.lower_bound)
            ub_list.append(p.upper_bound)
            if p.initial_guess is not None:
                p0_list.append(p.initial_guess)
            elif np.isfinite(p.lower_bound) and np.isfinite(p.upper_bound):
                p0_list.append((p.lower_bound + p.upper_bound) / 2.0)
            elif p.lower_bound > 0.0:
                p0_list.append(max(p.lower_bound * 1.5, 1.0))
            else:
                p0_list.append(1.0)

        p0 = np.array(p0_list, dtype=np.float64)
        lb = np.array(lb_list, dtype=np.float64)
        ub = np.array(ub_list, dtype=np.float64)

        # Clip p0 to strictly within bounds
        p0 = np.clip(p0, lb + 1e-8, ub - 1e-8)

        var_name = formula.independent_vars[0]

        def residuals(params: npt.NDArray[np.float64]) -> npt.NDArray[np.float64]:
            param_map = {p.name: float(params[i]) for i, p in enumerate(formula.parameters)}
            var_map = {var_name: x}
            try:
                pred = formula.evaluate(var_map, param_map)
                res = pred - y
                if not np.all(np.isfinite(res)):
                    return np.full_like(y, 1e12)
                return res
            except Exception:
                return np.full_like(y, 1e12)

        try:
            optimization = least_squares(
                residuals,
                p0,
                bounds=(lb, ub),
                method="trf",
                ftol=1e-8,
                xtol=1e-8,
                gtol=1e-8,
            )
        except Exception as exc:
            msg = f"Formula optimization failed for '{formula.name}': {exc}"
            raise ModelFitError(msg) from exc

        fitted_params = cast(npt.NDArray[np.float64], optimization.x)
        param_dict = {p.name: float(fitted_params[i]) for i, p in enumerate(formula.parameters)}
        init_param_dict = {p.name: float(p0[i]) for i, p in enumerate(formula.parameters)}

        # Evaluate final predictions
        fitted_y = formula.evaluate({var_name: x}, param_dict)
        errors = y - fitted_y
        rss = float(np.sum(errors**2))
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
        )

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
