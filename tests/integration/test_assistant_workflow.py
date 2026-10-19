"""End-to-end tests for the Phase 1 assistant workflow."""

import json
from pathlib import Path

import pytest

from scimodel.application.assistant_workflow import build_tool_registry, run_assistant
from scimodel.application.compare_models import compare_csv_models
from scimodel.application.providers import (
    DeterministicProvider,
    JsonPlanProvider,
    ProviderPlanError,
)
from scimodel.domain.assistant import TaskRequest
from scimodel.evaluation.runner import compare_evaluations, evaluate_suite, save_evaluation
from scimodel.infrastructure.context_store import ContextStore
from scimodel.infrastructure.recommendation_store import RecommendationStore
from scimodel.infrastructure.run_store import RunStore, compare_runs, redact_sensitive
from scimodel.interfaces.cli import main

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATASET = PROJECT_ROOT / "examples" / "enzyme_kinetics_synthetic.csv"
NEGATIVE_CONTROL = PROJECT_ROOT / "examples" / "non_kinetics_exponential_decay.csv"


def test_assistant_run_plans_executes_verifies_and_recommends(tmp_path: Path) -> None:
    request = TaskRequest("Analyze the enzyme kinetics data.", str(DATASET))

    run = run_assistant(request, tmp_path / "artifacts")

    assert run.status == "success"
    assert [call.tool for call in run.tool_calls] == [
        "inspect_data",
        "validate_model",
        "build_report",
    ]
    assert run.verification.passed
    assert run.recommendation["action"] == "domain_review"
    assert all(call.tool_version == "1.0" for call in run.tool_calls)
    assert all(call.error is None for call in run.tool_calls)
    assert (tmp_path / "artifacts" / "report.md").is_file()


def test_tool_registry_exposes_stable_schemas(tmp_path: Path) -> None:
    tools = build_tool_registry(tmp_path)

    assert [tool.schema.name for tool in tools] == [
        "inspect_data",
        "validate_model",
        "build_report",
    ]
    assert all(tool.schema.version == "1.0" for tool in tools)
    assert all(tool.schema.input_fields for tool in tools)
    assert all(tool.schema.output_fields for tool in tools)


def test_assistant_audit_mode_saves_structured_run_record(tmp_path: Path, capsys: object) -> None:
    assert (
        main(
            [
                "assistant",
                "run",
                str(DATASET),
                "--goal",
                "Validate this dataset",
                "--mode",
                "audit",
                "--output-dir",
                str(tmp_path),
            ]
        )
        == 0
    )

    record = json.loads((tmp_path / "assistant_run.json").read_text(encoding="utf-8"))
    assert record["status"] == "success"
    assert record["verification"]["passed"] is True
    assert len(record["tool_calls"]) == 3


def test_assistant_invalid_input_reports_failure(tmp_path: Path) -> None:
    request = TaskRequest("Analyze the data.", str(tmp_path / "missing.csv"))

    run = run_assistant(request, tmp_path / "artifacts")

    assert run.status == "failed"
    assert run.verification.passed is False
    assert run.tool_calls[0].status == "failed"
    assert run.tool_calls[0].error_category == "input"
    assert run.recommendation["action"] == "inspect_failure"


def test_run_store_lists_loads_compares_and_redacts(tmp_path: Path) -> None:
    request = TaskRequest("Analyze the data.", str(DATASET))
    run = run_assistant(request, tmp_path / "artifacts")
    store = RunStore(tmp_path / "history")

    run_id = store.save(run)
    loaded = store.load(run_id)
    comparison = compare_runs(loaded, loaded)

    assert loaded["run_id"] == run_id
    assert loaded["provider"]["name"] == "deterministic-rule-planner"
    assert store.list()[0]["run_id"] == run_id
    assert comparison["status_changed"] is False
    assert redact_sensitive({"api_key": "secret", "nested": {"password": "value"}}) == {
        "api_key": "[REDACTED]",
        "nested": {"password": "[REDACTED]"},
    }


def test_context_store_supports_review_update_and_removal(tmp_path: Path) -> None:
    store = ContextStore(tmp_path / "context")

    item = store.set(
        "preferred_detail",
        "concise but evidence-based",
        kind="preference",
        source="user instruction",
    )
    assert item.kind == "preference"
    assert store.get("preferred_detail")["value"] == "concise but evidence-based"
    assert store.set("preferred_detail", "detailed", kind="preference").value == "detailed"
    assert store.list()[0]["value"] == "detailed"
    store.remove("preferred_detail")
    assert store.list() == []


def test_assistant_records_context_snapshot(tmp_path: Path) -> None:
    request = TaskRequest("Analyze the data.", str(DATASET))
    context = ({"key": "project", "value": "kinetics", "status": "active"},)

    run = run_assistant(request, tmp_path / "artifacts", context)

    assert run.context == context


def test_recommendation_store_records_review_outcomes(tmp_path: Path) -> None:
    store = RecommendationStore(tmp_path / "recommendations")

    recommendation_id = store.save(
        {
            "action": "domain_review",
            "status": "pending",
            "evidence": ["validation.checks"],
        },
        "0123456789abcdef",
    )
    accepted = store.update(recommendation_id, "accepted", reason="Reviewer confirmed.")

    assert accepted["status"] == "accepted"
    assert accepted["reason"] == "Reviewer confirmed."
    assert store.list()[0]["recommendation_id"] == recommendation_id


def test_recommendation_cli_supports_review_lifecycle(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    recommendation_dir = tmp_path / "recommendations"
    history_dir = tmp_path / "history"
    output_dir = tmp_path / "run"
    result = main(
        [
            "assistant",
            "run",
            str(DATASET),
            "--goal",
            "Analyze the experiment",
            "--output-dir",
            str(output_dir),
            "--history-dir",
            str(history_dir),
            "--recommendation-dir",
            str(recommendation_dir),
        ]
    )
    assert result == 0
    recommendation_id = json.loads(capsys.readouterr().out)["recommendation"]["recommendation_id"]

    assert (
        main(
            ["assistant", "recommendation", "list", "--recommendation-dir", str(recommendation_dir)]
        )
        == 0
    )
    assert (
        main(
            [
                "assistant",
                "recommendation",
                "show",
                recommendation_id,
                "--recommendation-dir",
                str(recommendation_dir),
            ]
        )
        == 0
    )
    assert (
        main(
            [
                "assistant",
                "recommendation",
                "correct",
                recommendation_id,
                "--action",
                "collect_more_data",
                "--reason",
                "Need independent replicates.",
                "--recommendation-dir",
                str(recommendation_dir),
            ]
        )
        == 0
    )
    assert (
        main(
            [
                "assistant",
                "recommendation",
                "reject",
                recommendation_id,
                "--reason",
                "Superseded.",
                "--recommendation-dir",
                str(recommendation_dir),
            ]
        )
        == 0
    )


def test_context_cli_lifecycle(tmp_path: Path) -> None:
    context_dir = tmp_path / "context"
    assert (
        main(
            [
                "assistant",
                "context",
                "set",
                "style",
                "concise",
                "--kind",
                "preference",
                "--context-dir",
                str(context_dir),
            ]
        )
        == 0
    )
    assert main(["assistant", "context", "list", "--context-dir", str(context_dir)]) == 0
    assert main(["assistant", "context", "show", "style", "--context-dir", str(context_dir)]) == 0
    assert main(["assistant", "context", "remove", "style", "--context-dir", str(context_dir)]) == 0


def test_evaluation_suite_scores_supported_cases_and_compares(tmp_path: Path) -> None:
    report = evaluate_suite(PROJECT_ROOT, tmp_path / "evaluation")
    path = save_evaluation(report, tmp_path / "evaluation")
    comparison = compare_evaluations(report, json.loads(path.read_text(encoding="utf-8")))

    assert report["suite_version"] == "1.0"
    assert report["case_count"] == 3
    assert report["passed_cases"] == 3
    assert report["score"] == 1.0
    assert comparison["score_delta"] == 0.0


def test_formula_comparison_reports_candidates_without_selecting_one() -> None:
    comparison = compare_csv_models(DATASET)

    assert comparison["candidate_count"] == 2
    assert {candidate["model"] for candidate in comparison["candidates"]} == {
        "michaelis_menten",
        "hill_kinetics",
    }
    assert "do not establish physical correctness" in comparison["interpretation"]


def test_deterministic_provider_exposes_replaceable_plan_contract() -> None:
    provider = DeterministicProvider()
    plan = provider.create_plan(TaskRequest("Analyze data.", str(DATASET)))

    assert provider.provider_name == "deterministic-rule-planner"
    assert provider.provider_version == "1.0"
    assert [step.tool for step in plan] == [
        "inspect_data",
        "validate_model",
        "build_report",
    ]


def test_non_kinetics_negative_control_fails_scientific_validation(tmp_path: Path) -> None:
    run = run_assistant(
        TaskRequest(
            "Analyze the non-kinetics control.",
            str(NEGATIVE_CONTROL),
            x_column="time",
            y_column="concentration",
        ),
        tmp_path / "negative-control",
    )

    validation = next(
        call.output["validation"] for call in run.tool_calls if call.tool == "validate_model"
    )
    assert run.status == "failed"
    assert validation["valid"] is False
    assert validation["checks"][1]["name"] == "goodness_of_fit"
    assert validation["checks"][1]["passed"] is False


def test_json_provider_validates_external_plan_and_records_metadata(tmp_path: Path) -> None:
    plan_path = tmp_path / "provider-plan.json"
    plan_path.write_text(
        json.dumps(
            {
                "provider": "test-provider",
                "version": "2026.1",
                "steps": [
                    {
                        "step_id": "inspect",
                        "tool": "inspect_data",
                        "purpose": "Inspect input.",
                        "verification": "Input is valid.",
                    },
                    {
                        "step_id": "validate",
                        "tool": "validate_model",
                        "purpose": "Validate model.",
                        "verification": "Checks pass.",
                    },
                    {
                        "step_id": "report",
                        "tool": "build_report",
                        "purpose": "Build report.",
                        "verification": "Artifacts exist.",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    provider = JsonPlanProvider(plan_path)
    run = run_assistant(
        TaskRequest("Analyze data.", str(DATASET)), tmp_path / "run", provider=provider
    )

    assert run.status == "success"
    assert run.provider == {"name": "test-provider", "version": "2026.1", "model": None}
    invalid_plan = tmp_path / "invalid-plan.json"
    invalid_plan.write_text("{}", encoding="utf-8")
    with pytest.raises(ProviderPlanError):
        JsonPlanProvider(invalid_plan)
