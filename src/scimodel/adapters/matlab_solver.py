"""MATLAB Engine solver adapter for ModelFormula."""

from __future__ import annotations

import re

import numpy as np
import numpy.typing as npt

from scimodel.adapters.scipy_formula_solver import ScipyFormulaSolver
from scimodel.domain.fit import FitResult, ModelFitError
from scimodel.domain.formula import ModelFormula
from scimodel.domain.ports import ModelSolverPort


class MatlabUnavailableError(RuntimeError):
    """Raised when MATLAB or the MATLAB Engine API for Python is unavailable."""


def is_matlab_engine_installed() -> bool:
    """Check if the MATLAB Engine API for Python is importable."""
    try:
        import matlab.engine  # noqa: F401

        return True
    except (ImportError, ModuleNotFoundError):
        return False


def translate_formula_to_matlab(formula: ModelFormula) -> str:
    """Translate a ModelFormula expression into a vectorized MATLAB anonymous function.

    Example:
        Expression: '(Vmax * s) / (Km + s)'
        Parameters: ['Vmax', 'Km']
        Variable:   ['s']
        Output:     '@(p, s) (p(1) .* s) ./ (p(2) + s)'
    """
    expr = formula.expression

    # Vectorize arithmetic operators for MATLAB element-wise array evaluation
    expr = expr.replace("**", ".^")
    expr = re.sub(r"(?<!\.)\*", ".*", expr)
    expr = re.sub(r"(?<!\.)\/", "./", expr)

    # Map NumPy function names onto their MATLAB equivalents.
    for numpy_name, matlab_name in (("arctan", "atan"),):
        expr = re.sub(rf"\b{numpy_name}\(", f"{matlab_name}(", expr)

    # Substitute parameters with 1-indexed vector indexing p(1), p(2), ...
    for idx, param in enumerate(formula.parameters, start=1):
        expr = re.sub(rf"\b{re.escape(param.name)}\b", f"p({idx})", expr)

    # Construct anonymous function header @(p, var1, ...)
    vars_header = ", ".join(formula.independent_vars)
    return f"@(p, {vars_header}) {expr}"


class MatlabFormulaSolver(ModelSolverPort):
    """Optional solver adapter that executes nonlinear regression in MATLAB."""

    def __init__(self, *, fallback_to_scipy: bool = False) -> None:
        self.fallback_to_scipy = fallback_to_scipy

    @property
    def backend_name(self) -> str:
        return "matlab"

    def is_available(self) -> bool:
        """Return True if MATLAB Engine API for Python is installed."""
        return is_matlab_engine_installed()

    def fit(
        self,
        formula: ModelFormula,
        x: npt.NDArray[np.float64],
        y: npt.NDArray[np.float64],
    ) -> FitResult:
        """Fit formula parameters in MATLAB or optionally fallback to SciPy."""
        if not self.is_available():
            if self.fallback_to_scipy:
                scipy_solver = ScipyFormulaSolver()
                return scipy_solver.fit(formula, x, y)
            msg = (
                "MATLAB Engine API for Python is not installed or unlicensed. "
                "Install the MATLAB Engine for Python or use '--backend scipy'."
            )
            raise MatlabUnavailableError(msg)

        # MATLAB Engine execution
        try:
            import matlab
            import matlab.engine

            eng = matlab.engine.start_matlab()
        except Exception as exc:
            msg = f"Failed to initialize MATLAB engine: {exc}"
            raise MatlabUnavailableError(msg) from exc

        try:
            matlab_func_str = translate_formula_to_matlab(formula)
            f_handle = eng.eval(matlab_func_str)

            p0_list = [
                p.initial_guess
                if p.initial_guess is not None
                else ((p.lower_bound + p.upper_bound) / 2.0 if np.isfinite(p.upper_bound) else 1.0)
                for p in formula.parameters
            ]
            lb_list = [p.lower_bound for p in formula.parameters]
            ub_list = [p.upper_bound for p in formula.parameters]

            x_mat = matlab.double(x.tolist())
            y_mat = matlab.double(y.tolist())
            p0_mat = matlab.double(p0_list)
            lb_mat = matlab.double(lb_list)
            ub_mat = matlab.double(ub_list)

            # Call MATLAB's lsqcurvefit
            p_fitted, resnorm, _, exitflag, output, _, jacobian = eng.lsqcurvefit(
                f_handle,
                p0_mat,
                x_mat,
                y_mat,
                lb_mat,
                ub_mat,
                nargout=7,
            )

            p_vals = [float(val) for val in np.array(p_fitted).flatten()]
            param_dict = {p.name: p_vals[i] for i, p in enumerate(formula.parameters)}
            init_param_dict = {p.name: p0_list[i] for i, p in enumerate(formula.parameters)}

            # Evaluate predictions
            pred = formula.evaluate({formula.independent_vars[0]: x}, param_dict)
            rss = float(np.sum((y - pred) ** 2))
            rmse = float(np.sqrt(rss / len(y)))
            ss_tot = float(np.sum((y - np.mean(y)) ** 2))
            r_squared = 1.0 - (rss / ss_tot) if ss_tot > 0 else float("nan")

            converged = int(exitflag) > 0
            nfev = int(output.get("funcCount", 0)) if isinstance(output, dict) else 0

            return FitResult(
                model=formula.name,
                parameters=param_dict,
                standard_errors={p.name: float("nan") for p in formula.parameters},
                confidence_intervals={
                    p.name: (float("nan"), float("nan")) for p in formula.parameters
                },
                metrics={"rss": rss, "rmse": rmse, "r_squared": r_squared},
                initial_parameters=init_param_dict,
                converged=converged,
                function_evaluations=nfev,
                observations=len(y),
            )
        except Exception as exc:
            msg = f"MATLAB execution failed: {exc}"
            raise ModelFitError(msg) from exc
        finally:
            eng.quit()
