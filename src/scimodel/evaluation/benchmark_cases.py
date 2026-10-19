"""Deterministic benchmark cases for the supported assistant workflow."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from scimodel.domain.assistant import TaskRequest


@dataclass(frozen=True)
class BenchmarkCase:
    """One expected assistant behavior."""

    case_id: str
    description: str
    request: TaskRequest
    expected_status: str
    expected_tools: tuple[str, ...]
    expected_recommendation: str
    expected_error_category: str | None = None


def default_cases(project_root: Path) -> tuple[BenchmarkCase, ...]:
    synthetic = project_root / "examples" / "enzyme_kinetics_synthetic.csv"
    puromycin = project_root / "examples" / "enzyme_kinetics_puromycin.csv"
    return (
        BenchmarkCase(
            "synthetic_success",
            "Analyze the synthetic ground-truth dataset.",
            TaskRequest("Analyze the synthetic dataset.", str(synthetic)),
            "success",
            ("inspect_data", "validate_model", "build_report"),
            "domain_review",
        ),
        BenchmarkCase(
            "puromycin_success",
            "Analyze the Puromycin reference dataset.",
            TaskRequest("Analyze the Puromycin dataset.", str(puromycin)),
            "success",
            ("inspect_data", "validate_model", "build_report"),
            "domain_review",
        ),
        BenchmarkCase(
            "missing_input_failure",
            "Reject a missing input honestly.",
            TaskRequest("Analyze the missing dataset.", str(project_root / "missing.csv")),
            "failed",
            ("inspect_data",),
            "inspect_failure",
            "input",
        ),
    )
