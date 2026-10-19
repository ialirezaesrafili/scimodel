"""Domain result objects for model fitting."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


class ModelFitError(ValueError):
    """Raised when a model cannot be fitted to the supplied data."""


@dataclass(frozen=True)
class FitResult:
    """Auditable result of one model-fitting operation."""

    model: str
    parameters: dict[str, float]
    standard_errors: dict[str, float]
    confidence_intervals: dict[str, tuple[float, float]]
    metrics: dict[str, float]
    initial_parameters: dict[str, float]
    converged: bool
    function_evaluations: int
    observations: int
    parameter_correlation: dict[str, dict[str, float]] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable result representation."""
        result = asdict(self)
        result["status"] = "converged" if self.converged else "not_converged"
        return result
