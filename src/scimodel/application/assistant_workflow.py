"""Phase 1 deterministic assistant workflow around the SciModel engine."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from scimodel.application.inspect_data import inspect_csv
from scimodel.application.providers import DeterministicProvider
from scimodel.application.validate_kinetics import validate_csv
from scimodel.domain.assistant import (
    AssistantRun,
    PlanStep,
    TaskRequest,
    ToolCallRecord,
    ToolSchema,
    VerificationResult,
)
from scimodel.reporting.build_report import build_csv_report


@dataclass(frozen=True)
class RegisteredTool:
    """A narrow tool exposed to the assistant planner."""

    schema: ToolSchema
    execute: Callable[[TaskRequest], dict[str, Any]]

    @property
    def name(self) -> str:
        return self.schema.name


class ToolExecutionError(Exception):
    """Expected tool failure with a stable category for audit records."""

    def __init__(self, category: str, message: str) -> None:
        super().__init__(message)
        self.category = category


def build_plan(request: TaskRequest, provider: Any | None = None) -> tuple[PlanStep, ...]:
    """Create the tested plan using the default replaceable provider."""
    selected_provider = provider or DeterministicProvider()
    plan = tuple(selected_provider.create_plan(request))
    if not plan:
        raise ValueError("Provider returned an empty plan.")
    return plan


def build_tool_registry(output_dir: Path) -> tuple[RegisteredTool, ...]:
    """Return versioned tools implemented and permitted by the workflow."""

    def inspect(request: TaskRequest) -> dict[str, Any]:
        return inspect_csv(
            Path(request.input_path), x_column=request.x_column, y_column=request.y_column
        ).to_dict()

    def validate(request: TaskRequest) -> dict[str, Any]:
        result, validation = validate_csv(
            Path(request.input_path), x_column=request.x_column, y_column=request.y_column
        )
        return {"fit": result.to_dict(), "validation": validation.to_dict()}

    def report(request: TaskRequest) -> dict[str, Any]:
        artifacts, valid = build_csv_report(
            Path(request.input_path),
            output_dir,
            x_column=request.x_column,
            y_column=request.y_column,
        )
        return {"valid": valid, "artifacts": artifacts.to_dict()}

    return (
        RegisteredTool(
            ToolSchema(
                "inspect_data",
                "1.0",
                "Profile and validate the CSV input.",
                ("input_path", "x_column", "y_column"),
                ("valid", "issues", "columns"),
            ),
            inspect,
        ),
        RegisteredTool(
            ToolSchema(
                "validate_model",
                "1.0",
                "Fit and validate the supported kinetics model.",
                ("input_path", "x_column", "y_column"),
                ("fit", "validation"),
            ),
            validate,
        ),
        RegisteredTool(
            ToolSchema(
                "build_report",
                "1.0",
                "Create the report and machine-readable run artifacts.",
                ("input_path", "x_column", "y_column", "output_dir"),
                ("valid", "artifacts"),
            ),
            report,
        ),
    )


def run_assistant(
    request: TaskRequest,
    output_dir: Path,
    context: tuple[dict[str, Any], ...] = (),
    provider: Any | None = None,
) -> AssistantRun:
    """Execute the planned workflow and verify actual tool outputs."""
    selected_provider = provider or DeterministicProvider()
    plan = build_plan(request, selected_provider)
    tools = {tool.name: tool for tool in build_tool_registry(output_dir)}
    calls: list[ToolCallRecord] = []
    request_error = _validate_request(request)
    if request_error is not None:
        tool = tools[plan[0].tool]
        calls.append(
            ToolCallRecord(
                tool.name,
                tool.schema.version,
                _tool_input(request, tool.name, output_dir),
                "failed",
                {},
                request_error[1],
                request_error[0],
            )
        )
        return _finish_run(request, plan, calls, output_dir, context, selected_provider)
    for step in plan:
        registered_tool = tools.get(step.tool)
        if registered_tool is None:
            calls.append(
                ToolCallRecord(
                    step.tool,
                    "unknown",
                    {},
                    "failed",
                    {},
                    f"Provider requested an unregistered tool: {step.tool}",
                    "provider",
                )
            )
            break
        tool = registered_tool
        try:
            output = tool.execute(request)
        except Exception as exc:  # Convert tool failures into honest run evidence.
            category = _categorize_error(exc)
            calls.append(
                ToolCallRecord(
                    tool.name,
                    tool.schema.version,
                    _tool_input(request, tool.name, output_dir),
                    "failed",
                    {},
                    str(exc),
                    category,
                )
            )
            break
        calls.append(
            ToolCallRecord(
                tool.name,
                tool.schema.version,
                _tool_input(request, tool.name, output_dir),
                "succeeded",
                output,
            )
        )

    return _finish_run(request, plan, calls, output_dir, context, selected_provider)


def _finish_run(
    request: TaskRequest,
    plan: tuple[PlanStep, ...],
    calls: list[ToolCallRecord],
    output_dir: Path,
    context: tuple[dict[str, Any], ...],
    provider: Any,
) -> AssistantRun:
    """Build the result after successful or failed execution."""

    checks = _verify_run(plan, calls, output_dir)
    passed = all(bool(check["passed"]) for check in checks)
    validation_output = next(
        (call.output.get("validation") for call in calls if call.tool == "validate_model"), None
    )
    recommendation = _recommend(validation_output, passed, request)
    return AssistantRun(
        request=request,
        plan=plan,
        tool_calls=tuple(calls),
        verification=VerificationResult(passed, tuple(checks)),
        status="success" if passed else "failed",
        recommendation=recommendation,
        provider={
            "name": provider.provider_name,
            "version": provider.provider_version,
            "model": None,
        },
        approvals=(),
        context=context,
    )


def _validate_request(request: TaskRequest) -> tuple[str, str] | None:
    path = Path(request.input_path)
    if not request.objective.strip():
        return "request", "The assistant goal cannot be empty."
    if path.suffix.lower() != ".csv":
        return "input", "The Phase 2 workflow accepts CSV input only."
    if not path.is_file():
        return "input", f"Input file does not exist: {path}"
    if not request.x_column.strip() or not request.y_column.strip():
        return "request", "Both x_column and y_column must be non-empty."
    return None


def _tool_input(request: TaskRequest, tool_name: str, output_dir: Path) -> dict[str, Any]:
    values: dict[str, Any] = {
        "input_path": request.input_path,
        "x_column": request.x_column,
        "y_column": request.y_column,
    }
    if tool_name == "build_report":
        values["output_dir"] = str(output_dir)
    return values


def _categorize_error(error: Exception) -> str:
    if isinstance(error, ToolExecutionError):
        return error.category
    error_name = type(error).__name__
    if error_name in {"CsvReadError", "FileNotFoundError"}:
        return "input"
    if error_name == "ModelFitError":
        return "scientific"
    if isinstance(error, OSError):
        return "filesystem"
    return "unexpected"


def save_run(run: AssistantRun, output_dir: Path) -> Path:
    """Save the structured assistant audit record."""
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "assistant_run.json"
    path.write_text(json.dumps(run.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _verify_run(
    plan: tuple[PlanStep, ...], calls: list[ToolCallRecord], output_dir: Path
) -> list[dict[str, Any]]:
    expected = [step.tool for step in plan]
    actual = [call.tool for call in calls]
    checks: list[dict[str, Any]] = [
        {
            "name": "tool_trace_matches_plan",
            "passed": actual == expected,
            "expected": expected,
            "actual": actual,
        },
        {
            "name": "all_tools_succeeded",
            "passed": bool(calls) and all(call.status == "succeeded" for call in calls),
        },
    ]
    required = ("report.md", "fit_result.json", "validation.json", "run_manifest.json")
    checks.append(
        {
            "name": "report_artifacts_exist",
            "passed": all((output_dir / name).is_file() for name in required),
            "required": list(required),
        }
    )
    validation = next(
        (call.output.get("validation") for call in calls if call.tool == "validate_model"), None
    )
    checks.append(
        {
            "name": "scientific_validation_passed",
            "passed": bool(validation and validation.get("valid")),
        }
    )
    return checks


def _recommend(
    validation: dict[str, Any] | None,
    workflow_passed: bool,
    request: TaskRequest,
) -> dict[str, Any]:
    if not workflow_passed:
        return {
            "action": "inspect_failure",
            "reason": "The workflow did not pass verification; review the audit record and errors.",
            "evidence": ["assistant.verification"],
            "status": "pending",
        }
    failed = (
        [check["name"] for check in validation.get("checks", []) if not check["passed"]]
        if validation
        else []
    )
    if failed:
        return {
            "action": "review_failed_validation",
            "reason": "Validation requires scientific review before interpreting parameters.",
            "failed_checks": failed,
            "evidence": [f"validation.checks.{name}" for name in failed],
            "expected_benefit": "Prevent unsupported scientific interpretation.",
            "effort": "low",
            "uncertainty": "The failed check may reflect data quality or model mismatch.",
            "prerequisites": ["Inspect the failed validation checks."],
            "status": "pending",
        }
    return {
        "action": "domain_review",
        "reason": (
            "Review parameter estimates, uncertainty, assumptions, and limitations "
            "with domain knowledge."
        ),
        "prerequisite": (
            "A qualified scientific reviewer should confirm the model is appropriate "
            "for the experiment."
        ),
        "evidence": ["validation.checks", "validation.diagnostics", "validation.limitations"],
        "expected_benefit": "Confirm that the fitted model is scientifically appropriate.",
        "effort": "medium",
        "uncertainty": "A successful numerical fit does not prove physical correctness.",
        "prerequisites": ["Review parameter estimates, confidence intervals, and assumptions."],
        "goal": request.objective,
        "status": "pending",
    }
