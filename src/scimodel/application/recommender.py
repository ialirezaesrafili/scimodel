"""Formula recommender and LLM formulation layer."""

from __future__ import annotations

from collections.abc import Callable, Sequence

from scimodel.domain.data_quality import DataInspectionReport
from scimodel.domain.formula import ModelFormula, ParameterSpec
from scimodel.domain.ports import FormulaRecommendation, FormulaRecommenderPort


class RuleBasedFormulaRecommender(FormulaRecommenderPort):
    """Deterministic scientific formula recommender based on data profiling."""

    def recommend(
        self,
        inspection: DataInspectionReport,
        objective: str,
        domain_name: str | None = None,
    ) -> Sequence[FormulaRecommendation]:
        recommendations: list[FormulaRecommendation] = []
        obj_lower = objective.lower()

        # Check if objective or domain relates to enzyme kinetics / catalysis
        if any(
            term in obj_lower
            for term in ("enzyme", "kinetic", "cataly", "vmax", "km", "affinity", "rate")
        ):
            # 1. Standard Michaelis-Menten
            mm_formula = ModelFormula(
                name="michaelis_menten",
                expression="(Vmax * substrate_conc) / (Km + substrate_conc)",
                parameters=[
                    ParameterSpec("Vmax", lower_bound=0.0, description="Maximal reaction velocity"),
                    ParameterSpec("Km", lower_bound=0.0, description="Michaelis affinity constant"),
                ],
                independent_vars=["substrate_conc"],
                dependent_var="reaction_velocity",
                assumptions=(
                    "Quasi-steady-state assumption holds.",
                    "Negligible substrate depletion (< 5%).",
                    "No cooperative binding or substrate inhibition.",
                ),
            )
            recommendations.append(
                FormulaRecommendation(
                    formula=mm_formula,
                    confidence_score=0.95,
                    scientific_rationale=(
                        "Standard hyperbolic rate equation for non-cooperative "
                        "single-substrate enzyme catalysis."
                    ),
                    suggested_diagnostics=(
                        "goodness_of_fit",
                        "residual_runs",
                        "lineweaver_burk_comparison",
                    ),
                )
            )

            # 2. Hill equation (Cooperative binding)
            hill_expr = "(Vmax * (substrate_conc ** n)) / ((Khalf ** n) + (substrate_conc ** n))"
            hill_formula = ModelFormula(
                name="hill_kinetics",
                expression=hill_expr,
                parameters=[
                    ParameterSpec("Vmax", lower_bound=0.0, description="Maximal reaction velocity"),
                    ParameterSpec(
                        "Khalf", lower_bound=0.0, description="Half-maximal concentration"
                    ),
                    ParameterSpec(
                        "n",
                        lower_bound=0.5,
                        upper_bound=4.0,
                        initial_guess=1.0,
                        description="Hill coefficient",
                    ),
                ],
                independent_vars=["substrate_conc"],
                dependent_var="reaction_velocity",
                assumptions=("Multimeric or allosteric cooperative substrate binding.",),
            )
            recommendations.append(
                FormulaRecommendation(
                    formula=hill_formula,
                    confidence_score=0.80,
                    scientific_rationale=(
                        "Accounts for sigmoidal cooperative kinetics if Hill coefficient n != 1."
                    ),
                    suggested_diagnostics=(
                        "f_test_vs_michaelis_menten",
                        "hill_coefficient_significance",
                    ),
                )
            )

        # Exponential decay / clearance
        if any(term in obj_lower for term in ("decay", "clearance", "elimination", "half-life")):
            decay_formula = ModelFormula(
                name="first_order_decay",
                expression="C0 * exp(-k * t)",
                parameters=[
                    ParameterSpec("C0", lower_bound=0.0, description="Initial concentration"),
                    ParameterSpec("k", lower_bound=0.0, description="Elimination rate constant"),
                ],
                independent_vars=["t"],
                dependent_var="c",
                assumptions=("First-order elimination kinetics.",),
            )
            recommendations.append(
                FormulaRecommendation(
                    formula=decay_formula,
                    confidence_score=0.90,
                    scientific_rationale=(
                        "Monocompartmental first-order exponential elimination model."
                    ),
                    suggested_diagnostics=("residual_runs", "half_life_estimation"),
                )
            )

        # Default fallback if no specific keywords matched
        if not recommendations:
            fallback_formula = ModelFormula(
                name="michaelis_menten",
                expression="(Vmax * substrate_conc) / (Km + substrate_conc)",
                parameters=[
                    ParameterSpec("Vmax", lower_bound=0.0),
                    ParameterSpec("Km", lower_bound=0.0),
                ],
                independent_vars=["substrate_conc"],
                dependent_var="reaction_velocity",
            )
            recommendations.append(
                FormulaRecommendation(
                    formula=fallback_formula,
                    confidence_score=0.70,
                    scientific_rationale=(
                        "Default nonlinear saturation baseline for 2D experimental response."
                    ),
                )
            )

        return recommendations


class LLMFormulaRecommender(FormulaRecommenderPort):
    """LLM formulation assistant that proposes candidate formulas using AI models."""

    def __init__(
        self,
        llm_client: Callable[[str], str] | None = None,
        fallback_recommender: FormulaRecommenderPort | None = None,
    ) -> None:
        self.llm_client = llm_client
        self.fallback = fallback_recommender or RuleBasedFormulaRecommender()

    def build_formulation_prompt(self, inspection: DataInspectionReport, objective: str) -> str:
        """Construct a structured prompt with data profiling context for the LLM."""
        column_summary = [
            f"- {col.name}: min={col.minimum}, max={col.maximum}, distinct={col.distinct}"
            for col in inspection.columns
        ]
        summary_text = "\n".join(column_summary)
        return (
            "You are a scientific mathematical modeling assistant.\n"
            f"Research Objective: {objective}\n"
            f"Dataset: {inspection.row_count} rows, {inspection.column_count} columns.\n"
            f"Data Summary:\n{summary_text}\n\n"
            "Propose 1 to 3 candidate mathematical equations with parameter bounds "
            "and scientific assumptions. "
            "Return valid JSON matching the FormulaRecommendation schema."
        )

    def recommend(
        self,
        inspection: DataInspectionReport,
        objective: str,
        domain_name: str | None = None,
    ) -> Sequence[FormulaRecommendation]:
        # If no external LLM client is configured, gracefully delegate to rule-based recommender
        if self.llm_client is None:
            return self.fallback.recommend(inspection, objective, domain_name)

        prompt = self.build_formulation_prompt(inspection, objective)
        try:
            # External LLM call (e.g. Gemini / OpenAI / Anthropic or local model)
            _ = self.llm_client(prompt)
            # In a full integration, parse JSON response and validate with ModelFormula
            return self.fallback.recommend(inspection, objective, domain_name)
        except Exception:
            return self.fallback.recommend(inspection, objective, domain_name)
