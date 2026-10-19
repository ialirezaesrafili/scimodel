"""Unit tests for RuleBasedFormulaRecommender and LLMFormulaRecommender."""

from scimodel.application.recommender import (
    LLMFormulaRecommender,
    RuleBasedFormulaRecommender,
)
from scimodel.domain.data_quality import ColumnProfile, DataInspectionReport


def _create_mock_inspection() -> DataInspectionReport:
    return DataInspectionReport(
        source="test.csv",
        row_count=12,
        column_count=2,
        columns=(
            ColumnProfile(
                name="substrate_conc",
                non_empty=12,
                missing=0,
                numeric=True,
                distinct=6,
                minimum=0.02,
                maximum=1.10,
                mean=0.35,
            ),
            ColumnProfile(
                name="reaction_velocity",
                non_empty=12,
                missing=0,
                numeric=True,
                distinct=12,
                minimum=47.0,
                maximum=207.0,
                mean=141.5,
            ),
        ),
        duplicate_rows=0,
        issues=(),
    )


def test_rule_based_recommender_enzyme_kinetics() -> None:
    """Recommend Michaelis-Menten and Hill equations for enzyme kinetics objectives."""
    recommender = RuleBasedFormulaRecommender()
    inspection = _create_mock_inspection()

    recommendations = recommender.recommend(
        inspection, objective="Characterize enzyme substrate affinity and Vmax"
    )

    assert len(recommendations) >= 2
    names = [r.formula.name for r in recommendations]
    assert "michaelis_menten" in names
    assert "hill_kinetics" in names

    mm_rec = next(r for r in recommendations if r.formula.name == "michaelis_menten")
    assert mm_rec.confidence_score >= 0.90
    assert "substrate_conc" in mm_rec.formula.independent_vars


def test_rule_based_recommender_clearance() -> None:
    """Recommend exponential decay model for drug clearance or half-life objectives."""
    recommender = RuleBasedFormulaRecommender()
    inspection = _create_mock_inspection()

    recommendations = recommender.recommend(
        inspection, objective="Measure drug clearance and half-life decay"
    )

    names = [r.formula.name for r in recommendations]
    assert "first_order_decay" in names
    decay_rec = next(r for r in recommendations if r.formula.name == "first_order_decay")
    assert "exp" in decay_rec.formula.expression


def test_llm_formula_recommender_prompt_construction() -> None:
    """Verify prompt synthesis includes dataset row/column counts and variable ranges."""
    llm_recommender = LLMFormulaRecommender()
    inspection = _create_mock_inspection()

    prompt = llm_recommender.build_formulation_prompt(
        inspection, objective="Identify reaction saturation"
    )

    assert "Research Objective: Identify reaction saturation" in prompt
    assert "12 rows, 2 columns" in prompt
    assert "substrate_conc" in prompt
    assert "reaction_velocity" in prompt


def test_llm_formula_recommender_delegation() -> None:
    """LLM recommender delegates cleanly to fallback when no remote LLM client is configured."""
    recommender = LLMFormulaRecommender(llm_client=None)
    inspection = _create_mock_inspection()

    recommendations = recommender.recommend(inspection, objective="enzyme kinetics")
    assert len(recommendations) >= 1
    assert recommendations[0].formula.name == "michaelis_menten"


def test_rule_based_recommender_unmatched_objective_fallback() -> None:
    """Fallback to generic baseline when objective has no specific keywords."""
    recommender = RuleBasedFormulaRecommender()
    inspection = _create_mock_inspection()

    recommendations = recommender.recommend(inspection, objective="unrelated unknown process")
    assert len(recommendations) == 1
    assert recommendations[0].formula.name == "michaelis_menten"
    assert recommendations[0].confidence_score == 0.70


def test_llm_formula_recommender_client_call_and_exception() -> None:
    """Test LLM client invocation and fallback when client raises error."""

    def mock_client(prompt: str) -> str:
        return '{"result": "mock"}'

    recommender = LLMFormulaRecommender(llm_client=mock_client)
    inspection = _create_mock_inspection()

    recs = recommender.recommend(inspection, objective="enzyme catalysis")
    assert len(recs) >= 1

    def failing_client(prompt: str) -> str:
        raise RuntimeError("API timeout")

    failing_recommender = LLMFormulaRecommender(llm_client=failing_client)
    fallback_recs = failing_recommender.recommend(inspection, objective="enzyme catalysis")
    assert len(fallback_recs) >= 1
