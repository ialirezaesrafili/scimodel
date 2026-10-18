"""Application use case for fitting the approved kinetics model."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from scimodel.adapters.csv_reader import CsvTable, read_csv
from scimodel.adapters.scipy_solver import fit_michaelis_menten
from scimodel.application.inspect_data import inspect_table
from scimodel.domain.fit import FitResult, ModelFitError


def fit_csv(
    path: Path,
    *,
    x_column: str = "substrate_conc",
    y_column: str = "reaction_velocity",
) -> FitResult:
    """Inspect and fit one CSV dataset using Michaelis–Menten kinetics."""
    table = read_csv(path)
    return fit_table(table, source=str(path), x_column=x_column, y_column=y_column)


def fit_table(
    table: CsvTable,
    *,
    source: str = "<memory>",
    x_column: str = "substrate_conc",
    y_column: str = "reaction_velocity",
) -> FitResult:
    """Validate and fit one parsed table."""
    inspection = inspect_table(table, source=source, x_column=x_column, y_column=y_column)
    if not inspection.valid:
        errors = "; ".join(
            issue.message for issue in inspection.issues if issue.severity == "error"
        )
        raise ModelFitError(f"Data validation failed: {errors}")

    try:
        substrate = np.array([float(row[x_column]) for row in table.rows], dtype=float)
        velocity = np.array([float(row[y_column]) for row in table.rows], dtype=float)
    except (KeyError, ValueError) as exc:
        raise ModelFitError(f"Could not convert validated data to numeric arrays: {exc}") from exc
    return fit_michaelis_menten(substrate, velocity)
