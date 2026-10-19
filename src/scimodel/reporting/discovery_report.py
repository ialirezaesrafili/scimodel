"""Write a discovery report bundle: Markdown report, JSON results, manifest, figures."""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from scimodel.adapters.plotting import render_figures
from scimodel.application.discovery import refit_formulas
from scimodel.application.profiling import DatasetProfile
from scimodel.application.suggestions import next_steps
from scimodel.domain.dataset import Dataset
from scimodel.domain.discovery import CandidateResult, DiscoveryResult, ExpertiseLevel
from scimodel.infrastructure.reproducibility import build_manifest

GLOSSARY = {
    "R²": "Share of the variation in the data that the model explains (1 = all of it).",
    "Cross-validation": "Refitting the model without some points and predicting them, to test "
    "how well it generalizes to new data.",
    "AICc": "Akaike information criterion corrected for small samples: balances fit quality "
    "against the number of parameters. Lower is better; differences below 2 are not decisive.",
    "Akaike weight": "Approximate probability that a model is the best of those compared.",
    "Standard error": "Typical uncertainty of a fitted parameter.",
    "95% confidence interval": "Range that contains the true parameter value with 95% "
    "confidence if the model assumptions hold.",
    "Residual": "Difference between a measured value and the model's prediction.",
    "Pareto front": "Models for which no other model is both simpler and more accurate.",
    "Neural ceiling": "Prediction accuracy of a flexible neural network that assumes no "
    "equation; it shows how much structure is learnable from the data.",
}


@dataclass(frozen=True)
class ReportBundle:
    directory: Path
    report: Path
    results: Path
    manifest: Path
    figures: dict[str, str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "directory": str(self.directory),
            "report": str(self.report),
            "results": str(self.results),
            "manifest": str(self.manifest),
            "figures": self.figures,
        }


def write_discovery_report(
    result: DiscoveryResult,
    dataset: Dataset,
    profile: DatasetProfile,
    output_dir: Path,
    *,
    level: ExpertiseLevel = "intermediate",
    narrative: str | None = None,
    narrative_source: str | None = None,
) -> ReportBundle:
    """Write every artifact for one discovery run and return their paths."""
    output_dir.mkdir(parents=True, exist_ok=True)
    results_path = output_dir / "results.json"
    manifest_path = output_dir / "run_manifest.json"
    report_path = output_dir / "report.md"

    payload = result.to_dict()
    payload["profile"] = profile.to_dict()
    results_path.write_text(json.dumps(_clean(payload), indent=2) + "\n", encoding="utf-8")

    source = Path(dataset.source)
    manifest = (
        build_manifest(source, command="discover", configuration=_clean(result.settings))
        if source.is_file()
        else {"command": "discover", "configuration": _clean(result.settings)}
    )
    manifest["target"] = result.target
    manifest["predictors"] = list(result.predictors)
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    figures = _figures(result, dataset, output_dir / "figures")
    report_path.write_text(
        render_markdown(
            result,
            dataset,
            profile,
            level=level,
            figures=figures,
            narrative=narrative,
            narrative_source=narrative_source,
        ),
        encoding="utf-8",
    )
    return ReportBundle(output_dir, report_path, results_path, manifest_path, figures)


def render_markdown(
    result: DiscoveryResult,
    dataset: Dataset,
    profile: DatasetProfile,
    *,
    level: ExpertiseLevel = "intermediate",
    figures: dict[str, str] | None = None,
    narrative: str | None = None,
    narrative_source: str | None = None,
) -> str:
    figures = figures or {}
    best = result.best
    lines: list[str] = [f"# SciModel discovery report — {dataset.name}", ""]
    target_label = dataset.describe(result.target)
    predictor_labels = ", ".join(dataset.describe(p) for p in result.predictors)

    lines += ["## Summary", ""]
    if best is None:
        lines += ["No candidate formula could be fitted.", ""]
    else:
        assessment = result.quality.get(best.name)
        lines += [
            f"- **Question:** how does **{target_label}** depend on {predictor_labels}?",
            f"- **Recommended model:** `{best.name}` ({_origin(best)})",
            f"- **Equation:** `{result.target} = {_substituted(best)}`",
            f"- **Fit:** R² = {_fmt(best.fit.metrics.get('r_squared'))}, cross-validated R² = "
            f"{_fmt(best.cv_r_squared)}, {result.observations} observations",
        ]
        if assessment:
            lines.append(
                f"- **Quality grade:** {assessment.grade} ({assessment.score:.0f}/100) — "
                f"{assessment.verdict}"
            )
        runner_up = result.candidates[1] if len(result.candidates) > 1 else None
        if runner_up is not None:
            lines.append(
                f"- **Closest alternative:** `{runner_up.name}` "
                f"(ΔAICc = {_fmt(runner_up.delta_aicc, 3)}, "
                f"Akaike weight {_fmt(runner_up.akaike_weight, 2)})"
            )
        lines.append("")
        if level == "novice":
            lines += [
                "> **What this means.** SciModel tried many possible equations and kept the one "
                "that describes your measurements best *without* being needlessly complicated. "
                "The grade tells you how much to trust it; the sections below explain each check "
                "in plain language.",
                "",
            ]
    for warning in result.warnings:
        lines.append(f"> ⚠️ {warning}")
    if result.warnings:
        lines.append("")

    lines += _data_section(dataset, profile, level)
    if best is not None:
        lines += _best_model_section(result, best, dataset, figures, level)
        lines += _quality_section(result, best, level)
        lines += _leaderboard(result, level)
        lines += _baseline_section(result, best)
    lines += _engines_section(result)

    if narrative:
        lines += [
            "## AI interpretation",
            "",
            f"> Generated by a language model ({narrative_source or 'unknown'}) from the "
            "computed results above. It may contain errors; the numbers in the preceding "
            "sections are authoritative.",
            "",
            narrative.strip(),
            "",
        ]

    lines += ["## Suggested next steps", ""]
    for step in next_steps(result, profile):
        lines.append(
            f"- **{step.title}.** {step.rationale}" + (f" `{step.command}`" if step.command else "")
        )
    lines.append("")

    if level == "novice":
        lines += ["## Glossary", ""]
        lines += [f"- **{term}:** {definition}" for term, definition in GLOSSARY.items()]
        lines.append("")

    lines += [
        "## Reproducibility",
        "",
        f"- Input: `{dataset.source}` (SHA-256 in `run_manifest.json`)",
        f"- Engines: {', '.join(result.settings.get('engines', []))}; seed "
        f"{result.settings.get('seed')}; SciModel {result.settings.get('scimodel_version')}",
        "- All candidates, parameters, uncertainties, and checks: `results.json`",
        "",
        "Model selection uses the search-adjusted AICc (AICc + 2·ln M, where M is the number of "
        "structures an engine searched), a parsimony guard against parameters indistinguishable "
        "from zero, and a preference for mechanistic laws among statistically equivalent "
        "candidates (ΔAICc < 2). A good fit does not prove a mechanism: confirm with domain "
        "knowledge and new experiments.",
        "",
    ]
    return "\n".join(lines)


def _data_section(dataset: Dataset, profile: DatasetProfile, level: ExpertiseLevel) -> list[str]:
    lines = [
        "## Data",
        "",
        f"`{dataset.source}` — {profile.rows} rows, {len(profile.columns)} columns.",
        "",
    ]
    lines += ["| Column | Unit | Type | Role | Range | Missing |", "|---|---|---|---|---|---:|"]
    for column in profile.columns:
        value_range = (
            f"{_fmt(column.minimum)} … {_fmt(column.maximum)}"
            if column.minimum is not None
            else f"{column.distinct} categories"
        )
        lines.append(
            f"| {column.label} | {column.unit or ''} | {column.kind} | {column.role} | "
            f"{value_range} | {column.missing} |"
        )
    lines.append("")
    if profile.issues:
        lines += ["**Data-quality findings**", ""]
        lines += [
            f"- {issue.severity.upper()}: {issue.message}"
            + (f" (`{issue.column}`)" if issue.column else "")
            for issue in profile.issues
        ]
        lines.append("")
    for note in profile.notes:
        lines.append(f"- {note}")
    if level != "novice" and profile.relationships:
        lines += ["", "**Relationship screening**", ""]
        for item in profile.relationships:
            hints = ", ".join(item.hints) or "no strong shape"
            lines.append(
                f"- `{item.predictor}`: Spearman ρ = {item.spearman:.3f}; shape hints: {hints}"
            )
    lines.append("")
    return lines


def _best_model_section(
    result: DiscoveryResult,
    best: CandidateResult,
    dataset: Dataset,
    figures: dict[str, str],
    level: ExpertiseLevel,
) -> list[str]:
    lines = ["## Recommended model", "", f"```\n{result.target} = {best.expression}\n```", ""]
    lines += [f"*{best.rationale}*", ""]
    lines += ["| Parameter | Estimate | Std. error | 95% CI |", "|---|---:|---:|---:|"]
    for name, value in best.fit.parameters.items():
        low, high = best.fit.confidence_intervals.get(name, (math.nan, math.nan))
        lines.append(
            f"| {name} | {_fmt(value)} | {_fmt(best.fit.standard_errors.get(name))} | "
            f"[{_fmt(low)}, {_fmt(high)}] |"
        )
    lines.append("")
    metrics = best.fit.metrics
    lines += [
        f"RMSE = {_fmt(metrics.get('rmse'))} {dataset.units.get(result.target, '')}, "
        f"cross-validated RMSE = {_fmt(best.cv_rmse)}, AICc = {_fmt(best.aicc)}, "
        f"BIC = {_fmt(best.bic)}, complexity = {best.complexity}.",
        "",
    ]
    if best.assumptions:
        lines += ["**Assumptions behind this model**", ""]
        lines += [f"- {item}" for item in best.assumptions]
        lines.append("")
    for key, caption in (("fit", "Data and fitted model"), ("residuals", "Residuals")):
        if key in figures:
            lines += [f"![{caption}]({figures[key]})", ""]
    if level == "novice":
        lines += [
            "> Each parameter has an *estimate* and an *uncertainty*. If the confidence interval "
            "is narrow compared with the estimate, the data determine that parameter well.",
            "",
        ]
    return lines


def _quality_section(
    result: DiscoveryResult, best: CandidateResult, level: ExpertiseLevel
) -> list[str]:
    assessment = result.quality.get(best.name)
    if assessment is None:
        return []
    icon = {"pass": "✅", "warn": "⚠️", "fail": "❌", "skip": "➖"}
    lines = [f"## Quality assessment — grade {assessment.grade} ({assessment.score:.0f}/100)", ""]
    lines += [assessment.verdict, ""]
    if level == "novice":
        lines += ["| Check | Result | What it means |", "|---|---|---|"]
        lines += [
            f"| {c.name.replace('_', ' ')} | {icon[c.status]} | {c.explanation} |"
            for c in assessment.checks
        ]
    else:
        lines += ["| Check | Result | Detail |", "|---|---|---|"]
        lines += [
            f"| {c.name.replace('_', ' ')} | {icon[c.status]} {c.status} | {c.message} |"
            for c in assessment.checks
        ]
    lines.append("")
    return lines


def _leaderboard(result: DiscoveryResult, level: ExpertiseLevel) -> list[str]:
    limit = 6 if level == "novice" else 12
    lines = ["## Candidate models", ""]
    lines += [
        "| # | Model | Source | k | R² | CV R² | ΔAICc* | Weight | Grade |",
        "|---:|---|---|---:|---:|---:|---:|---:|---|",
    ]
    for rank, candidate in enumerate(result.candidates[:limit], start=1):
        grade = result.quality[candidate.name].grade if candidate.name in result.quality else ""
        pareto = " ◆" if candidate.name in result.pareto_front else ""
        lines.append(
            f"| {rank} | `{candidate.name}`{pareto} | {candidate.origin} | "
            f"{candidate.n_parameters} | {_fmt(candidate.fit.metrics.get('r_squared'), 4)} | "
            f"{_fmt(candidate.cv_r_squared, 4)} | {_fmt(candidate.delta_aicc, 3)} | "
            f"{_fmt(candidate.akaike_weight, 2)} | {grade} |"
        )
    lines += [
        "",
        f"*Search-adjusted ΔAICc. ◆ = on the accuracy/complexity Pareto front. "
        f"{len(result.candidates)} candidates were fitted in total.*",
        "",
    ]
    if level == "expert":
        lines += ["<details><summary>Expressions</summary>", ""]
        lines += [f"- `{c.name}`: `{c.expression}`" for c in result.candidates[:limit]]
        lines += ["", "</details>", ""]
    return lines


def _baseline_section(result: DiscoveryResult, best: CandidateResult) -> list[str]:
    neural = result.neural_baseline
    if not neural:
        return []
    lines = ["## Deep-learning ceiling", ""]
    if neural.get("status") != "ok":
        lines += [f"Skipped: {neural.get('reason')}", ""]
        return lines
    gap = float(neural["cv_r_squared"]) - best.cv_r_squared
    lines += [
        f"A {neural['architecture']} reached cross-validated R² = "
        f"{_fmt(neural['cv_r_squared'], 4)} without assuming any equation; the recommended "
        f"formula reaches {_fmt(best.cv_r_squared, 4)} (gap {gap:+.4f}).",
        "",
        "A gap near zero means the formula captures the learnable structure; a large positive "
        "gap means systematic behaviour remains unexplained. A negative gap is common on small "
        "datasets, where a compact law generalizes better than a network.",
        "",
    ]
    return lines


def _engines_section(result: DiscoveryResult) -> list[str]:
    lines = [
        "## Engines",
        "",
        "| Engine | Status | Proposals | Seconds | Note |",
        "|---|---|---:|---:|---|",
    ]
    lines += [
        f"| {e.engine} | {e.status} | {e.proposals} | {e.seconds:.2f} | {e.note} |"
        for e in result.engines
    ]
    lines.append("")
    if result.rejected:
        lines += [
            f"{len(result.rejected)} proposal(s) were rejected (invalid syntax, failed "
            "fits, or unsafe expressions); see `results.json`.",
            "",
        ]
    return lines


def _figures(result: DiscoveryResult, dataset: Dataset, directory: Path) -> dict[str, str]:
    best = result.best
    if best is None:
        return {}
    variables, y, _ = dataset.model_arrays(result.target, list(result.predictors))
    formula = refit_formulas(result)[best.name]
    try:
        fitted = np.broadcast_to(formula.evaluate(variables, best.fit.parameters), y.shape)
    except ValueError:
        return {}
    curve_x = curve_y = x = None
    if len(result.predictors) == 1:
        name = result.predictors[0]
        x = variables[name]
        curve_x = np.linspace(float(x.min()), float(x.max()), 400)
        try:
            curve_y = np.broadcast_to(
                formula.evaluate({name: curve_x}, best.fit.parameters), (400,)
            )
        except ValueError:
            curve_x = curve_y = None
    by_name = {c.name: c for c in result.candidates}
    pareto = [
        (by_name[name].complexity, by_name[name].cv_rmse, name)
        for name in result.pareto_front
        if name in by_name
    ]
    return render_figures(
        directory,
        x=x,
        x_label=dataset.describe(result.predictors[0]),
        y=y,
        y_label=dataset.describe(result.target),
        fitted=np.asarray(fitted, dtype=np.float64),
        curve_x=curve_x,
        curve_y=None if curve_y is None else np.asarray(curve_y, dtype=np.float64),
        pareto=pareto,
    )


def _substituted(candidate: CandidateResult) -> str:
    expression = candidate.expression
    for name, value in sorted(candidate.fit.parameters.items(), key=lambda item: -len(item[0])):
        expression = re.sub(rf"\b{re.escape(name)}\b", f"{value:.5g}", expression)
    return expression


def _origin(candidate: CandidateResult) -> str:
    return {
        "library": "established law" if candidate.mechanistic else "empirical curve",
        "sparse": "sparse-regression discovery",
        "symbolic": "symbolic-regression discovery",
        "llm": "AI-proposed hypothesis, verified numerically",
        "user": "your formula",
    }.get(candidate.origin, candidate.origin)


def _fmt(value: Any, digits: int = 5) -> str:
    if value is None:
        return "—"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if not math.isfinite(number):
        return "—"
    return f"{number:.{digits}g}"


def _clean(value: Any) -> Any:
    """Convert NaN/inf to None so the JSON is standard-compliant."""
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, dict):
        return {str(k): _clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_clean(item) for item in value]
    return value
