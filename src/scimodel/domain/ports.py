"""Application ports and protocols for scientific modeling solvers and recommenders."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Protocol

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


class LanguageModelError(RuntimeError):
    """Raised when a language-model provider cannot return a usable answer."""


class LanguageModelPort(Protocol):
    """Port for hosted or local language models used for reasoning, never computation."""

    @property
    def provider_name(self) -> str:
        """Stable provider identifier (e.g. 'anthropic', 'ollama')."""
        ...

    @property
    def model_name(self) -> str:
        """Model identifier used for requests."""
        ...

    def complete(
        self,
        system: str,
        prompt: str,
        *,
        json_schema: Mapping[str, Any] | None = None,
        max_tokens: int = 4096,
    ) -> str:
        """Return the model's text answer, JSON-encoded when a schema is given."""
        ...
