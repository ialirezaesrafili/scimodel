"""Application use case for validating a fitted kinetics model."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from scimodel.adapters.csv_reader import read_csv
from scimodel.application.fit_kinetics import fit_table
from scimodel.application.inspect_data import inspect_table
from scimodel.domain.fit import FitResult
from scimodel.domain.kinetics import michaelis_menten
from scimodel.domain.validation import ValidationCheck, ValidationResult


def validate_csv(
    path: Path,
    *,
    x_column: str = "substrate_conc",
    y_column: str = "reaction_velocity",
) -> tuple[FitResult, ValidationResult]:
    """Fit and validate a kinetics model against explicit checks."""
    table = read_csv(path)
    inspection = inspect_table(table, source=str(path), x_column=x_column, y_column=y_column)
    result = fit_table(table, source=str(path), x_column=x_column, y_column=y_column)
    substrate = np.array([float(row[x_column]) for row in table.rows], dtype=float)
    velocity = np.array([float(row[y_column]) for row in table.rows], dtype=float)
    predicted = michaelis_menten(
        substrate,
        result.parameters["vmax"],
        result.parameters["km"],
    )
    residuals = velocity - predicted
    signs = np.sign(residuals)
    sign_runs = int(1 + np.count_nonzero(signs[1:] * signs[:-1] < 0)) if len(signs) else 0
    diagnostics: dict[str, float | bool | int] = {
        "residual_mean": float(np.mean(residuals)),
        "residual_std": float(np.std(residuals, ddof=1)),
        "maximum_absolute_residual": float(np.max(np.abs(residuals))),
        "residual_sign_runs": sign_runs,
        "predictions_monotonic": bool(np.all(np.diff(predicted) >= 0)),
    }
    checks = (
        ValidationCheck(
            "convergence", result.converged, "The optimizer converged.", result.converged
        ),
        ValidationCheck(
            "goodness_of_fit",
            result.metrics["r_squared"] > 0.95,
            "R² is above the Phase 0 acceptance threshold of 0.95.",
            result.metrics["r_squared"],
        ),
        ValidationCheck(
            "physical_parameters",
            result.parameters["vmax"] > 0 and result.parameters["km"] > 0,
            "Vmax and Km are strictly positive.",
        ),
        ValidationCheck(
            "monotonic_predictions",
            bool(diagnostics["predictions_monotonic"]),
            "Predicted velocity is monotonic for the supplied concentrations.",
        ),
    )
    warnings: tuple[str, ...] = ()
    if abs(float(diagnostics["residual_mean"])) > result.metrics["rmse"]:
        warnings = ("Residual mean is large relative to RMSE; inspect possible systematic error.",)
    return result, ValidationResult(
        source=str(path),
        model=result.model,
        data_quality={
            "rows": inspection.row_count,
            "columns": inspection.column_count,
            "duplicate_rows": inspection.duplicate_rows,
            "error_count": sum(issue.severity == "error" for issue in inspection.issues),
            "warning_count": sum(issue.severity == "warning" for issue in inspection.issues),
        },
        diagnostics=diagnostics,
        checks=checks,
        assumptions=(
            "Michaelis–Menten quasi-steady-state behavior applies.",
            "Substrate depletion is negligible during the initial measurement window.",
            "Measurement errors are treated as additive and approximately homoscedastic.",
            "No cooperativity or substrate inhibition is assumed.",
        ),
        limitations=(
            "A successful fit does not prove physical correctness for every experiment.",
            "Confidence intervals reflect the fitted model and residual assumptions.",
            "Substrate inhibition and cooperative kinetics are outside this workflow.",
        ),
        warnings=warnings,
    )
