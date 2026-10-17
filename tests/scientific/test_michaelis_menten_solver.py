"""Known-answer tests for the Phase 3 Michaelis–Menten solver."""

from pathlib import Path

import numpy as np
import pytest

from scimodel.adapters.scipy_solver import fit_michaelis_menten
from scimodel.application.fit_kinetics import fit_csv
from scimodel.domain.fit import ModelFitError

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PUROMYCIN_CSV = PROJECT_ROOT / "examples" / "enzyme_kinetics_puromycin.csv"
SYNTHETIC_CSV = PROJECT_ROOT / "examples" / "enzyme_kinetics_synthetic.csv"


def test_puromycin_fit_matches_certified_reference() -> None:
    result = fit_csv(PUROMYCIN_CSV)

    assert result.converged
    assert abs(result.parameters["vmax"] - 212.684) < 0.50
    assert abs(result.parameters["km"] - 0.06412) < 0.0050
    assert abs(result.metrics["rss"] - 1195.45) < 10.0
    assert result.metrics["r_squared"] > 0.95
    assert abs(result.standard_errors["vmax"] - 6.947) < 0.50
    assert abs(result.standard_errors["km"] - 0.00828) < 0.0015
    assert result.confidence_intervals["vmax"][0] < 212.684 < result.confidence_intervals["vmax"][1]
    assert result.confidence_intervals["km"][0] < 0.06412 < result.confidence_intervals["km"][1]
    assert result.function_evaluations < 25


def test_synthetic_fit_recovers_ground_truth() -> None:
    result = fit_csv(SYNTHETIC_CSV)

    assert result.converged
    assert abs(result.parameters["vmax"] - 200.0) / 200.0 < 0.01
    assert abs(result.parameters["km"] - 0.05) / 0.05 < 0.01
    assert result.metrics["r_squared"] > 0.99


def test_fit_exposes_uncertainty_and_initialization() -> None:
    result = fit_csv(PUROMYCIN_CSV)

    assert set(result.parameters) == {"vmax", "km"}
    assert all(error >= 0 for error in result.standard_errors.values())
    assert all(
        result.confidence_intervals[name][0]
        < result.parameters[name]
        < result.confidence_intervals[name][1]
        for name in result.parameters
    )
    assert all(value > 0 for value in result.initial_parameters.values())


@pytest.mark.parametrize(
    ("substrate", "velocity", "message"),
    [
        (np.array([0.1, 0.2, 0.3]), np.array([10.0, 20.0, 30.0]), "At least 4 observations"),
        (np.array([0.1, 0.1, 0.1, 0.1]), np.array([10.0, 20.0, 30.0, 40.0]), "distinct"),
        (np.array([0.1, 0.2, np.nan, 0.4]), np.array([10.0, 20.0, 30.0, 40.0]), "finite"),
        (np.array([-0.1, 0.2, 0.3, 0.4]), np.array([10.0, 20.0, 30.0, 40.0]), "negative"),
    ],
)
def test_solver_rejects_unsupported_inputs(
    substrate: np.ndarray,
    velocity: np.ndarray,
    message: str,
) -> None:
    with pytest.raises(ModelFitError, match=message):
        fit_michaelis_menten(substrate, velocity)
