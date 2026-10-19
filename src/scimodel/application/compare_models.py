"""Compare explicitly recommended formulas without selecting one silently."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import numpy as np

from scimodel.adapters.csv_reader import read_csv
from scimodel.adapters.scipy_formula_solver import ScipyFormulaSolver
from scimodel.application.inspect_data import inspect_csv
from scimodel.application.recommender import RuleBasedFormulaRecommender
from scimodel.domain.fit import ModelFitError


def compare_csv_models(
    path: Path,
    *,
    objective: str = "enzyme kinetics",
    x_column: str = "substrate_conc",
    y_column: str = "reaction_velocity",
) -> dict[str, Any]:
    """Fit and compare candidate formulas recommended for one CSV input."""
    inspection = inspect_csv(path, x_column=x_column, y_column=y_column)
    if not inspection.valid:
        errors = "; ".join(
            issue.message for issue in inspection.issues if issue.severity == "error"
        )
        raise ModelFitError(f"Data validation failed: {errors}")
    table = read_csv(path)
    x_values = np.array([float(row[x_column]) for row in table.rows], dtype=float)
    y_values = np.array([float(row[y_column]) for row in table.rows], dtype=float)
    recommendations = RuleBasedFormulaRecommender().recommend(inspection, objective=objective)
    fits: list[dict[str, Any]] = []
    for recommendation in recommendations:
        result = ScipyFormulaSolver().fit(recommendation.formula, x_values, y_values)
        n = result.observations
        k = len(result.parameters)
        rss_value = float(result.metrics["rss"])
        rss = float(max(rss_value, float(np.finfo(float).tiny)))
        fits.append(
            {
                "model": result.model,
                "expression": recommendation.formula.expression,
                "confidence_score": recommendation.confidence_score,
                "scientific_rationale": recommendation.scientific_rationale,
                "fit": result.to_dict(),
                "information_criteria": {
                    "aic": float(n * math.log(rss / n) + 2 * k),
                    "bic": float(n * math.log(rss / n) + k * math.log(n)),
                },
            }
        )
    return {
        "source": str(path),
        "objective": objective,
        "candidate_count": len(fits),
        "candidates": fits,
        "interpretation": (
            "Information criteria compare statistical fit under these data and assumptions; "
            "they do not establish physical correctness or replace domain review."
        ),
    }
