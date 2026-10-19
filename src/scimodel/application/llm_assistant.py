"""Language-model reasoning layer: hypotheses, goal interpretation, and explanations.

Guardrails (see docs/decisions/0006):

* The model only sees a statistical *profile* of the data unless the user
  explicitly opts in to sharing a small sample of rows.
* Proposed formulas must pass the AST whitelist and are then fitted and
  validated locally exactly like any other candidate. The model never
  supplies numbers that appear in results.
* Narrative text is labelled as AI-generated in every report.
"""

from __future__ import annotations

import json
import math
import re
from collections.abc import Sequence
from typing import Any

from scimodel.application.profiling import DatasetProfile
from scimodel.domain.dataset import Dataset
from scimodel.domain.discovery import CandidateProposal, DiscoveryResult, ExpertiseLevel
from scimodel.domain.formula import ModelFormula, ParameterSpec
from scimodel.domain.ports import LanguageModelError, LanguageModelPort

SYSTEM_PROMPT = (
    "You are SciModel, a rigorous scientific modeling assistant working alongside a researcher. "
    "You reason about experimental data from summary statistics, propose mechanistically "
    "motivated mathematical models, and explain results honestly, including uncertainty and "
    "limitations. Never invent numerical results: every number you cite must come from the "
    "provided context. Prefer established scientific laws over ad hoc curve fitting, and say "
    "when the data cannot support a conclusion."
)

FORMULA_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "candidates": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "expression": {"type": "string"},
                    "parameters": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "initial_guess": {"type": "number"},
                                "lower_bound": {"type": ["number", "null"]},
                                "upper_bound": {"type": ["number", "null"]},
                            },
                            "required": ["name", "initial_guess", "lower_bound", "upper_bound"],
                            "additionalProperties": False,
                        },
                    },
                    "rationale": {"type": "string"},
                    "assumptions": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["name", "expression", "parameters", "rationale", "assumptions"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["candidates"],
    "additionalProperties": False,
}

GOAL_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "intent": {
            "type": "string",
            "enum": ["discover", "fit_specific", "quality", "explain", "report", "other"],
        },
        "target": {"type": ["string", "null"]},
        "predictors": {"type": "array", "items": {"type": "string"}},
        "formula": {"type": ["string", "null"]},
        "summary": {"type": "string"},
    },
    "required": ["intent", "target", "predictors", "formula", "summary"],
    "additionalProperties": False,
}

ALLOWED_FUNCTIONS_TEXT = (
    "Operators + - * / ** and functions exp, expm1, log, log10, log2, log1p, sqrt, sin, cos, "
    "tan, arctan, sinh, cosh, tanh, abs, and the constant pi."
)


def profile_context(
    profile: DatasetProfile, dataset: Dataset | None = None, *, share_sample: bool = False
) -> dict[str, Any]:
    """Build the privacy-preserving context sent to a language model."""
    context: dict[str, Any] = {
        "dataset": profile.dataset,
        "rows": profile.rows,
        "columns": [
            {
                "name": column.name,
                "label": column.label,
                "unit": column.unit,
                "kind": column.kind,
                "role": column.role,
                "min": column.minimum,
                "max": column.maximum,
                "mean": column.mean,
                "std": column.std,
                "distinct": column.distinct,
                "missing": column.missing,
            }
            for column in profile.columns
        ],
        "suggested_target": profile.target,
        "suggested_predictors": list(profile.predictors),
        "relationships": [
            {
                "predictor": item.predictor,
                "spearman": round(item.spearman, 4),
                "shape_hints": list(item.hints),
                "linearization_r2": {key: round(value, 4) for key, value in item.scores.items()},
            }
            for item in profile.relationships
        ],
        "issues": [issue.message for issue in profile.issues],
    }
    if share_sample and dataset is not None:
        rows = min(dataset.row_count, 25)
        context["sample_rows"] = [
            {
                name: (
                    None
                    if name in dataset.numeric and not math.isfinite(dataset.numeric[name][i])
                    else float(dataset.numeric[name][i])
                    if name in dataset.numeric
                    else dataset.categorical[name][i]
                )
                for name in dataset.columns
            }
            for i in range(rows)
        ]
    return context


class LLMResearchAssistant:
    """Grounded language-model helper with deterministic fallbacks."""

    def __init__(self, model: LanguageModelPort | None) -> None:
        self.model = model

    @property
    def available(self) -> bool:
        return self.model is not None

    def propose_formulas(
        self,
        context: dict[str, Any],
        *,
        target: str,
        predictors: Sequence[str],
        objective: str,
        max_candidates: int = 4,
    ) -> tuple[list[CandidateProposal], list[dict[str, str]]]:
        """Ask for candidate equations; return validated proposals and rejections."""
        if self.model is None:
            return [], []
        prompt = (
            f"Research objective: {objective or 'find the governing relationship'}\n"
            f"Target variable: {target}\nPredictor variables: {', '.join(predictors)}\n\n"
            f"Data profile (JSON):\n{json.dumps(context, indent=2, default=str)}\n\n"
            f"Propose up to {max_candidates} candidate equations for {target} as a function of "
            "the predictors. Favour mechanistic, established laws from the relevant scientific "
            "domain, and include at least one alternative hypothesis. Expressions must use only "
            f"the predictor names as variables, your parameter names, and: {ALLOWED_FUNCTIONS_TEXT}"
            " Give data-informed initial guesses and physically motivated bounds (null for "
            "unbounded)."
        )
        raw = self.model.complete(SYSTEM_PROMPT, prompt, json_schema=FORMULA_SCHEMA)
        return parse_formula_candidates(raw, target=target, predictors=predictors)

    def interpret_goal(
        self, goal: str, profile: DatasetProfile, context: dict[str, Any]
    ) -> dict[str, Any]:
        """Map a free-text research goal onto target, predictors, and intent."""
        fallback = interpret_goal_locally(goal, profile)
        if self.model is None:
            return fallback
        prompt = (
            f"The researcher says: {goal!r}\n\nData profile (JSON):\n"
            f"{json.dumps(context, indent=2, default=str)}\n\n"
            "Identify the intent, the target column, the predictor columns (use exact column "
            "names from the profile), and a formula if the researcher named one. Summarize "
            "what they want in one sentence."
        )
        try:
            answer = json.loads(self.model.complete(SYSTEM_PROMPT, prompt, json_schema=GOAL_SCHEMA))
        except (LanguageModelError, json.JSONDecodeError):
            return fallback
        if not isinstance(answer, dict):
            return fallback
        names = {column.name for column in profile.columns}
        if answer.get("target") not in names:
            answer["target"] = fallback["target"]
        answer["predictors"] = [p for p in answer.get("predictors", []) if p in names] or fallback[
            "predictors"
        ]
        answer["source"] = f"{self.model.provider_name}:{self.model.model_name}"
        return answer

    def explain_result(
        self, result: DiscoveryResult, level: ExpertiseLevel, objective: str = ""
    ) -> str | None:
        """Return a grounded narrative interpretation, or None without a model."""
        if self.model is None or result.best is None:
            return None
        audience = {
            "novice": "a student new to mathematical modeling; avoid jargon and define terms",
            "intermediate": "a researcher comfortable with regression",
            "expert": "a quantitative scientist; be concise and technical",
        }[level]
        summary = {
            "objective": objective,
            "target": result.target,
            "predictors": list(result.predictors),
            "observations": result.observations,
            "top_candidates": [
                {
                    "name": c.name,
                    "expression": c.expression,
                    "parameters": c.fit.parameters,
                    "standard_errors": c.fit.standard_errors,
                    "r_squared": c.fit.metrics.get("r_squared"),
                    "cv_r_squared": c.cv_r_squared,
                    "delta_aicc": c.delta_aicc,
                    "akaike_weight": c.akaike_weight,
                    "assumptions": list(c.assumptions),
                }
                for c in result.candidates[:5]
            ],
            "quality": {name: q.to_dict() for name, q in result.quality.items()},
            "neural_baseline": result.neural_baseline,
            "warnings": list(result.warnings),
        }
        prompt = (
            f"Explain these modeling results to {audience}.\n\n"
            f"Results (JSON):\n{json.dumps(summary, indent=2, default=str)}\n\n"
            "Cover: what relationship the data support, how confident we can be and why, what "
            "the parameters mean physically, competing explanations, the main risks or "
            "limitations, and 2-4 concrete next experiments or analyses. Use Markdown with "
            "short sections. Cite only numbers present in the results."
        )
        try:
            return self.model.complete(SYSTEM_PROMPT, prompt, max_tokens=6000)
        except LanguageModelError:
            return None

    def answer(self, question: str, context: dict[str, Any]) -> str:
        if self.model is None:
            raise LanguageModelError(
                "No language model is configured. Run 'scimodel config set llm_provider "
                "anthropic' (or 'ollama' for a local model)."
            )
        prompt = (
            f"Context (JSON):\n{json.dumps(context, indent=2, default=str)}\n\n"
            f"Researcher question: {question}"
        )
        return self.model.complete(SYSTEM_PROMPT, prompt, max_tokens=6000)


def parse_formula_candidates(
    raw: str, *, target: str, predictors: Sequence[str]
) -> tuple[list[CandidateProposal], list[dict[str, str]]]:
    """Validate model-proposed formulas; never execute anything that fails the AST whitelist."""
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return [], [{"expression": raw[:200], "reason": "Response was not valid JSON."}]
    items = payload.get("candidates", []) if isinstance(payload, dict) else []
    proposals: list[CandidateProposal] = []
    rejected: list[dict[str, str]] = []
    for index, item in enumerate(items if isinstance(items, list) else []):
        expression = str(item.get("expression", ""))
        try:
            specs = []
            for spec in item.get("parameters", []):
                lower = spec.get("lower_bound")
                upper = spec.get("upper_bound")
                specs.append(
                    ParameterSpec(
                        str(spec["name"]),
                        lower_bound=-math.inf if lower is None else float(lower),
                        upper_bound=math.inf if upper is None else float(upper),
                        initial_guess=float(spec.get("initial_guess", 1.0)),
                    )
                )
            used = [name for name in predictors if _mentions(expression, name)]
            if not used:
                raise ValueError("The expression does not use any predictor.")
            formula = ModelFormula(
                name=f"llm_{_slug(str(item.get('name', index + 1)))}",
                expression=expression,
                parameters=specs,
                independent_vars=list(predictors),
                dependent_var=target,
                assumptions=tuple(str(a) for a in item.get("assumptions", [])),
            )
        except (KeyError, TypeError, ValueError) as exc:
            rejected.append({"expression": expression, "reason": str(exc)})
            continue
        start = {spec.name: float(spec.initial_guess or 1.0) for spec in specs}
        proposals.append(
            CandidateProposal(
                formula, "llm", f"AI-proposed hypothesis: {item.get('rationale', '')}", (start,)
            )
        )
    return proposals, rejected


def _mentions(expression: str, name: str) -> bool:
    return re.search(rf"\b{re.escape(name)}\b", expression) is not None


def _slug(text: str) -> str:
    return re.sub(r"[^0-9a-zA-Z]+", "_", text).strip("_").lower()[:40] or "candidate"


def interpret_goal_locally(goal: str, profile: DatasetProfile) -> dict[str, Any]:
    """Keyword-based goal interpretation used when no language model is configured."""
    text = goal.lower()
    mentioned = [
        column.name
        for column in profile.columns
        if column.kind == "numeric"
        and (column.name.lower() in text or column.label.lower() in text)
    ]
    target = profile.target
    predictors = list(profile.predictors)
    for marker in (" of ", " for ", "predict ", "explain ", "model "):
        if marker in text:
            after = text.split(marker, 1)[1]
            for name in mentioned:
                column = profile.column(name)
                label = column.label.lower() if column else name.lower()
                if after.startswith(name.lower()) or after.startswith(label):
                    target = name
                    break
    if target in mentioned and len(mentioned) > 1:
        predictors = [name for name in mentioned if name != target]
    elif target is not None:
        predictors = [name for name in predictors if name != target]
    intent = "discover"
    if any(word in text for word in ("quality", "clean", "outlier", "missing")):
        intent = "quality"
    elif any(word in text for word in ("report", "write up", "summary")):
        intent = "report"
    elif "explain" in text and "?" in text:
        intent = "explain"
    return {
        "intent": intent,
        "target": target,
        "predictors": predictors,
        "formula": None,
        "summary": goal.strip() or "Discover the relationship in the data.",
        "source": "local-keywords",
    }
