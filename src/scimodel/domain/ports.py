"""Application ports and protocols for scientific modeling solvers and recommenders."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

import numpy as np
import numpy.typing as npt

from scimodel.domain.data_quality import DataInspectionReport
from scimodel.domain.fit import FitResult
from scimodel.domain.formula import ModelFormula


class ModelSolverPort(Protocol):
    """Port for mathematical model solvers."""

    @property
    def backend_name(self) -> str:
        """Name of the solver backend (e.g. 'scipy', 'matlab')."""
        ...

    def is_available(self) -> bool:
        """Return True if backend engine and licenses are available."""
        ...

    def fit(
        self,
        formula: ModelFormula,
        x: npt.NDArray[np.float64],
        y: npt.NDArray[np.float64],
    ) -> FitResult:
        """Fit formula parameters to data and return unified FitResult."""
        ...


@dataclass(frozen=True)
class FormulaRecommendation:
    """A candidate formula proposed by a recommender or LLM assistant."""

    formula: ModelFormula
    confidence_score: float
    scientific_rationale: str
    suggested_diagnostics: Sequence[str] = ()


class FormulaRecommenderPort(Protocol):
    """Port for AI/LLM mathematical formulation assistants."""

    def recommend(
        self,
        inspection: DataInspectionReport,
        objective: str,
        domain_name: str | None = None,
    ) -> Sequence[FormulaRecommendation]:
        """Propose candidate mathematical formulas for the inspected dataset."""
        ...
