"""Domain contracts for formula discovery, ranking, and quality assessment."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

from scimodel.domain.fit import FitResult
from scimodel.domain.formula import ModelFormula

ExpertiseLevel = Literal["novice", "intermediate", "expert"]
EXPERTISE_LEVELS: tuple[ExpertiseLevel, ...] = ("novice", "intermediate", "expert")
CheckStatus = Literal["pass", "warn", "fail", "skip"]
CandidateOrigin = Literal["library", "sparse", "symbolic", "llm", "user"]


@dataclass(frozen=True)
class CandidateProposal:
    """A formula proposed by an engine before it has been fitted."""

    formula: ModelFormula
    origin: CandidateOrigin
    rationale: str
    starts: tuple[dict[str, float], ...] = ()
    mechanistic: bool = False
    search_space: int = 1


@dataclass(frozen=True)
class CandidateResult:
    """A fitted and scored candidate formula."""

    name: str
    expression: str
    origin: CandidateOrigin
    rationale: str
    fit: FitResult
    complexity: int
    n_parameters: int
    aic: float
    aicc: float
    bic: float
    cv_rmse: float
    cv_r_squared: float
    assumptions: tuple[str, ...] = ()
    mechanistic: bool = False
    search_penalty: float = 0.0
    delta_aicc: float = float("nan")
    akaike_weight: float = float("nan")

    @property
    def adjusted_aicc(self) -> float:
        """AICc plus the structure-search penalty 2·ln(M) of the proposing engine."""
        return self.aicc + self.search_penalty

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["fit"] = self.fit.to_dict()
        result["adjusted_aicc"] = self.adjusted_aicc
        return result


@dataclass(frozen=True)
class QualityCheck:
    """One quality assertion with a technical and a plain-language message."""

    name: str
    status: CheckStatus
    message: str
    explanation: str
    value: float | int | str | None = None


@dataclass(frozen=True)
class QualityAssessment:
    """Aggregated quality verdict for one fitted candidate."""

    candidate: str
    checks: tuple[QualityCheck, ...]
    score: float
    grade: str
    verdict: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EngineRun:
    """Audit record of one discovery engine execution."""

    engine: str
    status: Literal["ok", "skipped", "failed"]
    proposals: int
    seconds: float
    note: str = ""


@dataclass(frozen=True)
class DiscoveryResult:
    """Complete, serializable record of one discovery run."""

    dataset: str
    source: str
    target: str
    predictors: tuple[str, ...]
    observations: int
    dropped_rows: int
    candidates: tuple[CandidateResult, ...]
    pareto_front: tuple[str, ...]
    quality: dict[str, QualityAssessment]
    engines: tuple[EngineRun, ...]
    settings: dict[str, Any]
    neural_baseline: dict[str, Any] | None = None
    rejected: tuple[dict[str, str], ...] = ()
    warnings: tuple[str, ...] = field(default_factory=tuple)

    @property
    def best(self) -> CandidateResult | None:
        return self.candidates[0] if self.candidates else None

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset": self.dataset,
            "source": self.source,
            "target": self.target,
            "predictors": list(self.predictors),
            "observations": self.observations,
            "dropped_rows": self.dropped_rows,
            "best": self.best.name if self.best else None,
            "candidates": [candidate.to_dict() for candidate in self.candidates],
            "pareto_front": list(self.pareto_front),
            "quality": {name: item.to_dict() for name, item in self.quality.items()},
            "engines": [asdict(engine) for engine in self.engines],
            "settings": self.settings,
            "neural_baseline": self.neural_baseline,
            "rejected": list(self.rejected),
            "warnings": list(self.warnings),
        }
