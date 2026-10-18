"""Application use case for inspecting a CSV dataset."""

from __future__ import annotations

import math
from pathlib import Path
from statistics import fmean

from scimodel.adapters.csv_reader import CsvTable, read_csv
from scimodel.domain.data_quality import ColumnProfile, DataInspectionReport, DataIssue


def inspect_csv(
    path: Path,
    *,
    x_column: str = "substrate_conc",
    y_column: str = "reaction_velocity",
) -> DataInspectionReport:
    """Profile a CSV and apply the approved Phase 0 kinetics checks."""
    table = read_csv(path)
    return inspect_table(table, source=str(path), x_column=x_column, y_column=y_column)


def inspect_table(
    table: CsvTable,
    *,
    source: str = "<memory>",
    x_column: str = "substrate_conc",
    y_column: str = "reaction_velocity",
) -> DataInspectionReport:
    """Profile a parsed table without changing its source values."""
    issues: list[DataIssue] = []
    profiles = tuple(_profile_column(table, header) for header in table.headers)
    duplicate_rows = len(table.rows) - len(
        {tuple(row[h] for h in table.headers) for row in table.rows}
    )

    if not table.rows:
        issues.append(DataIssue("empty_dataset", "error", "The CSV contains no data rows."))
    if duplicate_rows:
        issues.append(
            DataIssue(
                "duplicate_rows",
                "warning",
                f"The dataset contains {duplicate_rows} duplicate row(s).",
            )
        )

    for profile in profiles:
        if profile.missing:
            issues.append(
                DataIssue(
                    "missing_values",
                    "warning",
                    f"Column contains {profile.missing} missing value(s).",
                    column=profile.name,
                )
            )
        if profile.distinct == 1 and profile.non_empty:
            issues.append(
                DataIssue(
                    "constant_column",
                    "warning",
                    "Column has only one distinct non-empty value.",
                    column=profile.name,
                )
            )

    _validate_kinetics_columns(table, issues, x_column=x_column, y_column=y_column)
    return DataInspectionReport(
        source=source,
        row_count=len(table.rows),
        column_count=len(table.headers),
        columns=profiles,
        duplicate_rows=duplicate_rows,
        issues=tuple(issues),
    )


def _profile_column(table: CsvTable, header: str) -> ColumnProfile:
    values = [row[header] for row in table.rows]
    present = [value for value in values if value != ""]
    numbers = [_to_float(value) for value in present]
    numeric = bool(present) and all(number is not None for number in numbers)
    numeric_values = [number for number in numbers if number is not None]
    return ColumnProfile(
        name=header,
        non_empty=len(present),
        missing=len(values) - len(present),
        numeric=numeric,
        distinct=len(set(present)),
        minimum=min(numeric_values) if numeric else None,
        maximum=max(numeric_values) if numeric else None,
        mean=fmean(numeric_values) if numeric else None,
    )


def _validate_kinetics_columns(
    table: CsvTable,
    issues: list[DataIssue],
    *,
    x_column: str,
    y_column: str,
) -> None:
    for column in (x_column, y_column):
        if column not in table.headers:
            issues.append(
                DataIssue(
                    "missing_required_column",
                    "error",
                    f"Required kinetics column is missing: {column}.",
                    column=column,
                )
            )

    if any(issue.code == "missing_required_column" for issue in issues):
        return

    x_values = [_to_float(row[x_column]) for row in table.rows]
    y_values = [_to_float(row[y_column]) for row in table.rows]
    for column, values in ((x_column, x_values), (y_column, y_values)):
        if any(value is None or not math.isfinite(value) for value in values):
            issues.append(
                DataIssue(
                    "non_numeric_value",
                    "error",
                    "Required kinetics column contains missing, non-numeric, or non-finite values.",
                    column=column,
                )
            )

    if any(value is not None and value < 0 for value in x_values):
        issues.append(
            DataIssue(
                "negative_concentration",
                "error",
                "Substrate concentrations cannot be negative.",
                x_column,
            )
        )
    if any(value is not None and value < 0 for value in y_values):
        issues.append(
            DataIssue(
                "negative_velocity", "error", "Reaction velocities cannot be negative.", y_column
            )
        )
    if len({value for value in x_values if value is not None}) < 4:
        issues.append(
            DataIssue(
                "insufficient_concentration_levels",
                "error",
                "At least 4 distinct substrate concentration levels are required.",
                x_column,
            )
        )


def _to_float(value: str) -> float | None:
    if value == "":
        return None
    try:
        return float(value)
    except ValueError:
        return None
