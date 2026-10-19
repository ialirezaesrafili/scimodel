"""Discover, fit, rank, and assess candidate formulas for any dataset.

Pipeline::

    proposals  ← model library ∪ sparse regression ∪ symbolic regression
                 ∪ language-model hypotheses ∪ user formulas
    fit        ← multi-start bounded least squares (SciPy TRF)
    score      ← AIC, AICc, BIC, k-fold cross-validation, complexity
    rank       ← AICc with Akaike weights; Pareto front of accuracy vs complexity
    assess     ← quality checks against residuals, replicates, and a neural ceiling

Engines are independent and failure-isolated: one failing engine is recorded
in the audit trail and never aborts the run.
"""

from __future__ import annotations

import math
import re
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field, replace
from typing import Any, TypeAlias

import numpy as np
import numpy.typing as npt

from scimodel import __version__
from scimodel.adapters.neural_surrogate import NeuralBaseline, NeuralSettings
from scimodel.adapters.scipy_formula_solver import ScipyFormulaSolver
from scimodel.adapters.sparse_regression import SparseRegressor
from scimodel.adapters.symbolic_regression import (
    DEFAULT_UNARY_OPS,
    PERIODIC_UNARY_OPS,
    SymbolicRegressor,
    SymbolicSearchSettings,
)
from scimodel.application.llm_assistant import LLMResearchAssistant, profile_context
from scimodel.application.model_library import multivariate_templates, univariate_templates
from scimodel.application.profiling import DatasetProfile, profile_dataset
from scimodel.application.quality import assess_candidate
from scimodel.domain.dataset import Dataset, DatasetError
from scimodel.domain.discovery import (
    CandidateProposal,
    CandidateResult,
    DiscoveryResult,
    EngineRun,
    QualityAssessment,
)
from scimodel.domain.fit import ModelFitError
from scimodel.domain.formula import (
    RESERVED_NAMES,
    FormulaEvaluationError,
    FormulaSyntaxError,
    ModelFormula,
    ParameterSpec,
)
from scimodel.domain.ports import LanguageModelError, LanguageModelPort

FloatArray: TypeAlias = npt.NDArray[np.float64]
ENGINES = ("library", "sparse", "symbolic", "neural", "llm")
DEFAULT_ENGINES = ("library", "sparse", "symbolic", "neural", "llm")
Progress = Callable[[str], None]


@dataclass(frozen=True)
class DiscoveryOptions:
    engines: tuple[str, ...] = DEFAULT_ENGINES
    seed: int = 0
    time_budget: float = 15.0
    cv_folds: int = 5
    assess_top: int = 3
    objective: str = ""
    user_formulas: tuple[str, ...] = ()
    language_model: LanguageModelPort | None = None
    share_data_sample: bool = False
    max_univariate_predictors: int = 4
    extra: dict[str, Any] = field(default_factory=dict)


def discover(
    dataset: Dataset,
    *,
    target: str,
    predictors: Sequence[str],
    options: DiscoveryOptions | None = None,
    profile: DatasetProfile | None = None,
    progress: Progress | None = None,
) -> DiscoveryResult:
    """Run every enabled engine and return a ranked, assessed result."""
    options = options or DiscoveryOptions()
    unknown = sorted(set(options.engines) - set(ENGINES))
    if unknown:
        raise DatasetError(f"Unknown engine(s): {', '.join(unknown)}. Choose from {ENGINES}.")
    say = progress or (lambda _message: None)
    variables, y, dropped = dataset.model_arrays(target, list(predictors))
    n = len(y)
    if n < 5:
        raise DatasetError(f"Only {n} complete rows: at least 5 are needed for discovery.")
    if float(np.ptp(y)) == 0:
        raise DatasetError(f"The target '{target}' is constant; there is nothing to model.")
    profile = profile or profile_dataset(dataset, target=target, predictors=tuple(predictors))

    proposals: list[CandidateProposal] = []
    engines: list[EngineRun] = []
    rejected: list[dict[str, str]] = []
    warnings: list[str] = []
    if dropped:
        warnings.append(f"{dropped} row(s) with missing values were excluded.")

    def run_engine(name: str, action: Callable[[], list[CandidateProposal]]) -> None:
        if name not in options.engines:
            engines.append(EngineRun(name, "skipped", 0, 0.0, "Disabled by options."))
            return
        say(f"engine: {name}")
        started = time.monotonic()
        try:
            produced = action()
        except (LanguageModelError, ModelFitError, ValueError, np.linalg.LinAlgError) as exc:
            engines.append(EngineRun(name, "failed", 0, time.monotonic() - started, str(exc)))
            return
        proposals.extend(produced)
        engines.append(EngineRun(name, "ok", len(produced), round(time.monotonic() - started, 3)))

    def library() -> list[CandidateProposal]:
        produced: list[CandidateProposal] = []
        for name in list(predictors)[: options.max_univariate_predictors]:
            column = profile.column(name)
            produced.extend(
                _restrict(
                    univariate_templates(
                        name,
                        variables[name],
                        y,
                        target,
                        profile.relationship(name),
                        column.role if column else "measurement",
                    ),
                    predictors,
                )
            )
        produced.extend(multivariate_templates(variables, y, target))
        return [replace(item, search_space=len(produced)) for item in produced]

    def sparse() -> list[CandidateProposal]:
        return SparseRegressor().propose(variables, y, target=target)

    def symbolic() -> list[CandidateProposal]:
        oscillating = any("oscillating" in item.hints for item in profile.relationships)
        unary = DEFAULT_UNARY_OPS + (PERIODIC_UNARY_OPS if oscillating else ())
        settings = SymbolicSearchSettings(
            seed=options.seed, time_budget=options.time_budget, unary_ops=unary
        )
        return SymbolicRegressor(settings).propose(variables, y, target=target)

    def llm() -> list[CandidateProposal]:
        if options.language_model is None:
            raise LanguageModelError("No language model configured.")
        assistant = LLMResearchAssistant(options.language_model)
        context = profile_context(profile, dataset, share_sample=options.share_data_sample)
        produced, refused = assistant.propose_formulas(
            context, target=target, predictors=predictors, objective=options.objective
        )
        rejected.extend(refused)
        return [replace(item, search_space=max(len(produced), 1)) for item in produced]

    run_engine("library", library)
    run_engine("sparse", sparse)
    run_engine("symbolic", symbolic)
    if "llm" in options.engines and options.language_model is None:
        engines.append(EngineRun("llm", "skipped", 0, 0.0, "No language model configured."))
    else:
        run_engine("llm", llm)
    for index, expression in enumerate(options.user_formulas, start=1):
        try:
            proposals.append(_user_proposal(expression, predictors, target, index))
        except (FormulaSyntaxError, ValueError) as exc:
            rejected.append({"expression": expression, "reason": str(exc)})

    say(f"fitting {len(proposals)} candidate formulas")
    candidates, formulas = _fit_all(proposals, variables, y, options, rejected)
    if not candidates:
        raise ModelFitError("No candidate formula could be fitted to the data.")
    ranked = _rank(candidates)
    pareto = _pareto(ranked)

    neural: dict[str, Any] | None = None
    if "neural" in options.engines:
        say("engine: neural (deep-learning ceiling)")
        started = time.monotonic()
        neural = NeuralBaseline(
            NeuralSettings(seed=options.seed, time_budget=max(options.time_budget, 10.0))
        ).evaluate(variables, y)
        engines.append(
            EngineRun(
                "neural",
                "ok" if neural.get("status") == "ok" else "skipped",
                0,
                round(time.monotonic() - started, 3),
                str(neural.get("reason", neural.get("architecture", ""))),
            )
        )
    else:
        engines.append(EngineRun("neural", "skipped", 0, 0.0, "Disabled by options."))
    ceiling = float(neural["cv_r_squared"]) if neural and neural.get("status") == "ok" else None

    say("assessing model quality")
    quality: dict[str, QualityAssessment] = {}
    to_assess = list(
        dict.fromkeys([c.name for c in ranked[: options.assess_top]] + list(pareto[:2]))
    )
    for name in to_assess:
        candidate = next(c for c in ranked if c.name == name)
        quality[name] = assess_candidate(
            candidate, formulas[name], variables, y, neural_cv_r_squared=ceiling
        )

    if n < 4 * max(c.n_parameters for c in ranked[:1]):
        warnings.append(
            "Few observations per parameter: rankings between similar models are uncertain."
        )
    if ceiling is not None and ranked[0].cv_r_squared < ceiling - 0.1:
        warnings.append(
            "The neural ceiling is well above the best formula: unexplained structure remains; "
            "consider additional predictors or mechanisms."
        )

    settings = {
        "engines": list(options.engines),
        "seed": options.seed,
        "time_budget_seconds": options.time_budget,
        "cv_folds": options.cv_folds,
        "objective": options.objective,
        "language_model": (
            f"{options.language_model.provider_name}:{options.language_model.model_name}"
            if options.language_model
            else None
        ),
        "share_data_sample": options.share_data_sample,
        "scimodel_version": __version__,
    }
    return DiscoveryResult(
        dataset=dataset.name,
        source=dataset.source,
        target=target,
        predictors=tuple(predictors),
        observations=n,
        dropped_rows=dropped,
        candidates=tuple(ranked),
        pareto_front=tuple(pareto),
        quality=quality,
        engines=tuple(engines),
        settings=settings,
        neural_baseline=neural,
        rejected=tuple(rejected),
        warnings=tuple(warnings),
    )


def _restrict(
    proposals: list[CandidateProposal], predictors: Sequence[str]
) -> list[CandidateProposal]:
    """Give single-predictor templates the full variable list and a unique name."""
    restricted = []
    suffix = len(predictors) > 1
    for proposal in proposals:
        formula = proposal.formula
        name = f"{formula.name}[{formula.independent_vars[0]}]" if suffix else formula.name
        restricted.append(
            replace(
                proposal,
                formula=ModelFormula(
                    name=name,
                    expression=formula.expression,
                    parameters=formula.parameters,
                    independent_vars=list(predictors),
                    dependent_var=formula.dependent_var,
                    assumptions=formula.assumptions,
                ),
            )
        )
    return restricted


def _user_proposal(
    expression: str, predictors: Sequence[str], target: str, index: int
) -> CandidateProposal:
    tokens = dict.fromkeys(re.findall(r"\b[a-zA-Z_][a-zA-Z0-9_]*\b", expression))
    names = [t for t in tokens if t not in RESERVED_NAMES and t not in predictors]
    if not any(re.search(rf"\b{re.escape(p)}\b", expression) for p in predictors):
        raise ValueError("The formula does not use any predictor column.")
    formula = ModelFormula(
        name=f"user_{index}",
        expression=expression,
        parameters=[ParameterSpec(name, -math.inf, math.inf, 1.0) for name in names],
        independent_vars=list(predictors),
        dependent_var=target,
    )
    return CandidateProposal(
        formula, "user", "Formula supplied by the researcher.", mechanistic=True
    )


def _fit_all(
    proposals: Sequence[CandidateProposal],
    variables: dict[str, FloatArray],
    y: FloatArray,
    options: DiscoveryOptions,
    rejected: list[dict[str, str]],
) -> tuple[list[CandidateResult], dict[str, ModelFormula]]:
    solver = ScipyFormulaSolver(jacobian_scaling=True)
    plain = ScipyFormulaSolver()
    # Fold refits start at the full-data optimum, so a small budget suffices; an
    # unconverged refit still returns its best point, which CV then scores honestly.
    fold_solver = ScipyFormulaSolver(max_evaluations=60)
    results: list[CandidateResult] = []
    formulas: dict[str, ModelFormula] = {}
    seen_expressions: set[str] = set()
    folds = _folds(len(y), options.cv_folds, options.seed)
    for proposal in proposals:
        formula = proposal.formula
        key = formula.expression.replace(" ", "")
        if key in seen_expressions:
            continue
        seen_expressions.add(key)
        name = formula.name
        while name in formulas:
            name = f"{name}'"
        if len(formula.parameters) >= len(y) - 1:
            rejected.append({"expression": formula.expression, "reason": "Too many parameters."})
            continue
        try:
            fits = []
            for engine in (solver, plain):
                try:
                    fits.append(engine.fit(formula, variables, y, starts=proposal.starts))
                except ModelFitError:
                    continue
            if not fits:
                raise ModelFitError("All optimizer configurations failed.")
            fit = min(fits, key=lambda item: item.metrics["rss"])
        except (ModelFitError, FormulaEvaluationError) as exc:
            rejected.append({"expression": formula.expression, "reason": str(exc)})
            continue
        if not math.isfinite(fit.metrics["rss"]):
            continue
        n, k = len(y), len(formula.parameters)
        rss = max(fit.metrics["rss"], 1e-300)
        log_likelihood_term = n * math.log(rss / n)
        aic = log_likelihood_term + 2 * (k + 1)
        aicc = aic + (2 * (k + 1) * (k + 2)) / (n - k - 2) if n - k - 2 > 0 else math.inf
        bic = log_likelihood_term + (k + 1) * math.log(n)
        cv_rmse, cv_r2 = _cross_validate(fold_solver, formula, fit.parameters, variables, y, folds)
        fit = replace(fit, model=name)
        formulas[name] = formula
        results.append(
            CandidateResult(
                name=name,
                expression=formula.expression,
                origin=proposal.origin,
                rationale=proposal.rationale,
                fit=fit,
                complexity=formula.complexity,
                n_parameters=k,
                aic=aic,
                aicc=aicc,
                bic=bic,
                cv_rmse=cv_rmse,
                cv_r_squared=cv_r2,
                assumptions=tuple(formula.assumptions),
                mechanistic=proposal.mechanistic,
                search_penalty=2.0 * math.log(max(proposal.search_space, 1)),
            )
        )
    return results, formulas


def _folds(n: int, k: int, seed: int) -> list[npt.NDArray[np.intp]]:
    k = n if n < 10 else min(k, n)
    order = np.random.default_rng(seed).permutation(n)
    return [fold for fold in np.array_split(order, k) if len(fold)]


def _cross_validate(
    solver: ScipyFormulaSolver,
    formula: ModelFormula,
    parameters: dict[str, float],
    variables: dict[str, FloatArray],
    y: FloatArray,
    folds: Sequence[npt.NDArray[np.intp]],
) -> tuple[float, float]:
    predictions = np.full_like(y, np.nan)
    for test in folds:
        train = np.setdiff1d(np.arange(len(y)), test)
        if len(train) <= len(formula.parameters):
            return math.nan, math.nan
        train_vars = {name: values[train] for name, values in variables.items()}
        test_vars = {name: values[test] for name, values in variables.items()}
        try:
            fold_fit = solver.fit(formula, train_vars, y[train], starts=(parameters,))
            predictions[test] = np.broadcast_to(
                formula.evaluate(test_vars, fold_fit.parameters), test.shape
            )
        except (ModelFitError, FormulaEvaluationError):
            return math.nan, math.nan
    if not np.all(np.isfinite(predictions)):
        return math.nan, math.nan
    sse = float(np.sum((y - predictions) ** 2))
    sst = float(np.sum((y - y.mean()) ** 2))
    return math.sqrt(sse / len(y)), (1 - sse / sst) if sst > 0 else math.nan


def has_redundant_parameters(candidate: CandidateResult) -> bool:
    """True when some parameter cannot be distinguished from zero (|estimate| < SE)."""
    for name, value in candidate.fit.parameters.items():
        error = candidate.fit.standard_errors.get(name, math.nan)
        if not math.isfinite(error) or abs(value) < error:
            return True
    return False


ORIGIN_PRIORITY = {"user": 0, "library": 1, "llm": 2, "sparse": 3, "symbolic": 4}
EQUIVALENCE_WINDOW = 2.0


def _rank(candidates: list[CandidateResult]) -> list[CandidateResult]:
    """Order candidates by evidence, with two documented scientific guards.

    The criterion is the *search-adjusted* AICc: AICc + 2·ln(M), where M is
    the number of model structures the proposing engine searched. This is the
    AIC analogue of a uniform prior over the searched structures and stops
    expression search from winning merely by trying thousands of shapes.

    1. Parsimony guard: candidates containing a parameter indistinguishable
       from zero (|estimate| < SE) rank after fully identified candidates.
    2. Interpretability tie-break: among candidates within 2 units of the
       best (statistically equivalent support, Burnham & Anderson 2002),
       mechanistic laws precede empirical curves, researcher and library
       formulas precede data-mined expressions, then fewer parameters win.
    """

    def aicc(candidate: CandidateResult) -> float:
        value = candidate.adjusted_aicc
        return value if math.isfinite(value) else candidate.aic + candidate.search_penalty + 1e6

    ordered = sorted(candidates, key=lambda c: (has_redundant_parameters(c), aicc(c), c.complexity))
    leader = aicc(ordered[0])
    window = [
        c
        for c in ordered
        if not has_redundant_parameters(c) and aicc(c) - leader < EQUIVALENCE_WINDOW
    ]
    window.sort(
        key=lambda c: (not c.mechanistic, ORIGIN_PRIORITY.get(c.origin, 9), c.n_parameters, aicc(c))
    )
    rest = [c for c in ordered if c not in window]
    ordered = window + rest
    best = min(aicc(c) for c in ordered)
    deltas = [aicc(c) - best for c in ordered]
    raw = [math.exp(-0.5 * d) if d < 1400 else 0.0 for d in deltas]
    total = sum(raw) or 1.0
    return [
        replace(c, delta_aicc=d, akaike_weight=w / total)
        for c, d, w in zip(ordered, deltas, raw, strict=True)
    ]


def _pareto(candidates: list[CandidateResult]) -> list[str]:
    usable = [c for c in candidates if math.isfinite(c.cv_rmse)]
    front: list[str] = []
    best = math.inf
    for candidate in sorted(usable, key=lambda c: (c.complexity, c.cv_rmse)):
        if candidate.cv_rmse < best * (1 - 1e-6):
            front.append(candidate.name)
            best = candidate.cv_rmse
    return front


def refit_formulas(result: DiscoveryResult) -> dict[str, ModelFormula]:
    """Reconstruct formula objects from a result (used by reporting)."""
    formulas: dict[str, ModelFormula] = {}
    for candidate in result.candidates:
        formulas[candidate.name] = ModelFormula(
            name=candidate.name,
            expression=candidate.expression,
            parameters=[
                ParameterSpec(name, -math.inf, math.inf, value)
                for name, value in candidate.fit.parameters.items()
            ],
            independent_vars=list(result.predictors),
            dependent_var=result.target,
        )
    return formulas
