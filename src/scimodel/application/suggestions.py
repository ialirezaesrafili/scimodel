"""Evidence-based suggestions: what a researcher can do with a dataset, and what to do next."""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from typing import Any

from scimodel.application.profiling import DatasetProfile
from scimodel.domain.discovery import DiscoveryResult, ExpertiseLevel

_SHAPE_ADVICE = {
    "saturating": "The response levels off: saturation laws (Michaelis–Menten, Langmuir, Monod) "
    "or a first-order approach to a plateau are plausible.",
    "sigmoidal": "The response is S-shaped: logistic, Gompertz, or Hill models are plausible.",
    "power_law_like": "log–log plot is nearly straight: a power law y = A·x^k is plausible.",
    "exponential_like": "semi-log plot is nearly straight: exponential growth or decay is "
    "plausible.",
    "oscillating": "The response oscillates: harmonic or damped-oscillator models are plausible.",
    "peak": "The response has an interior maximum: a peak (Gaussian) or optimum model is "
    "plausible.",
    "valley": "The response has an interior minimum: an optimum or oscillation model is plausible.",
    "linear_like": "The relationship is close to a straight line.",
    "accelerating": "The response accelerates: power-law, exponential, or Arrhenius forms are "
    "plausible.",
    "weak_relationship": "There is little monotonic association; check whether this predictor "
    "matters at all.",
}


@dataclass(frozen=True)
class Suggestion:
    """One actionable option presented to the researcher."""

    kind: str
    title: str
    rationale: str
    command: str = ""
    priority: int = 50
    params: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def suggest_actions(
    profile: DatasetProfile, *, level: ExpertiseLevel = "intermediate", path: str | None = None
) -> list[Suggestion]:
    """Return prioritized options for a freshly profiled dataset."""
    source = path or profile.source
    suggestions: list[Suggestion] = []
    target, predictors = profile.target, list(profile.predictors)
    numeric = [c for c in profile.columns if c.kind == "numeric" and c.role != "index"]

    errors = [issue for issue in profile.issues if issue.severity == "error"]
    warnings = [issue for issue in profile.issues if issue.severity == "warning"]
    if errors or warnings:
        suggestions.append(
            Suggestion(
                "quality",
                "Review data-quality findings first",
                f"{len(errors)} error(s) and {len(warnings)} warning(s) were found "
                "(missing values, outliers, small sample). Models inherit these problems.",
                f"scimodel profile {source}",
                priority=10 if errors else 30,
            )
        )

    if target and predictors:
        joined = ",".join(predictors)
        suggestions.append(
            Suggestion(
                "discover",
                f"Discover the equation for {target} from {', '.join(predictors)}",
                "Search established scientific laws, sparse regression, and symbolic regression; "
                "rank by evidence and grade the quality of the best models.",
                f"scimodel discover {source} --target {target} --predictors {joined}",
                priority=20,
                params={"target": target, "predictors": predictors},
            )
        )
        for relationship in profile.relationships:
            for hint in relationship.hints:
                if hint in _SHAPE_ADVICE:
                    suggestions.append(
                        Suggestion(
                            "insight",
                            f"{relationship.predictor} → {target}: {hint.replace('_', ' ')}",
                            _SHAPE_ADVICE[hint],
                            priority=40,
                        )
                    )
        if len(predictors) > 1:
            for predictor in predictors:
                suggestions.append(
                    Suggestion(
                        "discover",
                        f"Isolate the effect of {predictor}",
                        f"Model {target} using {predictor} alone to judge whether the other "
                        "predictors are needed.",
                        f"scimodel discover {source} --target {target} --predictors {predictor}",
                        priority=60,
                        params={"target": target, "predictors": [predictor]},
                    )
                )
    elif len(numeric) < 2:
        suggestions.append(
            Suggestion(
                "data",
                "Add a second numeric variable",
                "Modeling needs a response and at least one numeric predictor.",
                priority=5,
            )
        )

    if profile.replicated_predictor_levels:
        suggestions.append(
            Suggestion(
                "insight",
                "Replicates detected — lack-of-fit testing is available",
                "Repeated settings let SciModel separate measurement noise from model error.",
                priority=45,
            )
        )
    grouping = [c for c in profile.columns if c.role == "grouping"]
    if grouping:
        names = ", ".join(c.name for c in grouping)
        suggestions.append(
            Suggestion(
                "insight",
                f"Grouping column(s) found: {names}",
                "Fit groups separately to compare conditions, or confirm they are only labels.",
                priority=55,
            )
        )
    suggestions.append(
        Suggestion(
            "fit",
            "Test your own hypothesis",
            "Fit a formula you already have in mind and compare it with discovered models.",
            f'scimodel discover {source} --target {target or "y"} --formula "A*x/(K + x)"',
            priority=70,
        )
    )
    if level == "novice":
        suggestions.append(
            Suggestion(
                "learn",
                "Ask what any result means",
                "In the interactive session, type a question such as 'what is R²?' or "
                "'is my model good enough?'.",
                priority=80,
            )
        )
    return sorted(suggestions, key=lambda item: item.priority)


def next_steps(result: DiscoveryResult, profile: DatasetProfile) -> list[Suggestion]:
    """Recommend follow-up work based on the discovery evidence."""
    steps: list[Suggestion] = []
    best = result.best
    if best is None:
        return [Suggestion("data", "Revisit the data", "No model could be fitted.")]
    assessment = result.quality.get(best.name)
    failed = {c.name for c in assessment.checks if c.status == "fail"} if assessment else set()
    warned = {c.name for c in assessment.checks if c.status == "warn"} if assessment else set()

    close = [c for c in result.candidates[1:4] if math.isfinite(c.delta_aicc) and c.delta_aicc < 2]
    if close:
        names = ", ".join(f"`{c.name}`" for c in close)
        steps.append(
            Suggestion(
                "experiment",
                "Design a discriminating experiment",
                f"{names} are statistically equivalent to the best model. Measure where their "
                "predictions differ most (often at the extremes of the predictor range).",
                priority=10,
            )
        )
    if "residual_independence" in failed | warned or "lack_of_fit" in failed:
        steps.append(
            Suggestion(
                "model",
                "Look for a missing mechanism",
                "Residuals are structured: an additional process, predictor, or regime change "
                "may be at work.",
                priority=15,
            )
        )
    if "constant_variance" in warned:
        steps.append(
            Suggestion(
                "model",
                "Use a weighted or log-scale fit",
                "Measurement scatter changes with the response; relative-error weighting gives "
                "more reliable uncertainties.",
                priority=30,
            )
        )
    if "parameter_identifiability" in failed | warned or "parameter_correlation" in failed:
        steps.append(
            Suggestion(
                "experiment",
                "Extend the measurement range",
                "Some parameters are poorly determined; data over a wider predictor range "
                "(for example, beyond the half-saturation point) would pin them down.",
                priority=20,
            )
        )
    if "predictor_relevance" in warned:
        steps.append(
            Suggestion(
                "model",
                "Try a simpler model without negligible predictors",
                "At least one predictor barely changes the prediction.",
                f"scimodel discover {result.source} --target {result.target} --predictors "
                + ",".join(_relevant(result)),
                priority=12,
            )
        )
    if "outlier_sensitivity" in failed | warned:
        steps.append(
            Suggestion(
                "data",
                "Inspect influential points",
                "A few observations noticeably change the parameters; verify them against lab "
                "records before excluding anything.",
                priority=25,
            )
        )
    neural = result.neural_baseline or {}
    if neural.get("status") == "ok" and float(neural["cv_r_squared"]) - best.cv_r_squared > 0.05:
        steps.append(
            Suggestion(
                "model",
                "Close the gap to the neural ceiling",
                "A flexible model predicts better: consider interaction terms, extra predictors, "
                "or a longer symbolic search (--time-budget 60).",
                priority=18,
            )
        )
    if result.observations < 20:
        steps.append(
            Suggestion(
                "experiment",
                "Collect more observations",
                f"With {result.observations} points, only large differences between models are "
                "detectable.",
                priority=35,
            )
        )
    steps.append(
        Suggestion(
            "review",
            "Confirm with domain knowledge",
            "Check that parameter values are physically sensible and the assumptions hold for "
            "your experiment.",
            priority=90,
        )
    )
    return sorted(steps, key=lambda item: item.priority)


def _relevant(result: DiscoveryResult) -> list[str]:
    best = result.best
    if best is None:
        return list(result.predictors)
    assessment = result.quality.get(best.name)
    flagged: set[str] = set()
    if assessment:
        for check in assessment.checks:
            if check.name == "predictor_relevance" and isinstance(check.value, str):
                flagged = {item.strip() for item in check.value.split(",")}
    kept = [p for p in result.predictors if p not in flagged]
    return kept or list(result.predictors)
