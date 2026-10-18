"""Run and score assistant benchmark cases."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scimodel import __version__
from scimodel.application.assistant_workflow import run_assistant
from scimodel.evaluation.benchmark_cases import default_cases

SUITE_VERSION = "1.0"


def evaluate_suite(project_root: Path, output_dir: Path) -> dict[str, Any]:
    """Execute all benchmark cases and return a scored evaluation report."""
    results: list[dict[str, Any]] = []
    for case in default_cases(project_root):
        run = run_assistant(case.request, output_dir / case.case_id)
        actual_tools = tuple(call.tool for call in run.tool_calls)
        error_categories = [call.error_category for call in run.tool_calls if call.error_category]
        checks = {
            "status": run.status == case.expected_status,
            "tool_selection": actual_tools == case.expected_tools,
            "verification": run.verification.passed == (case.expected_status == "success"),
            "recommendation": run.recommendation.get("action") == case.expected_recommendation,
            "error_category": case.expected_error_category is None
            or case.expected_error_category in error_categories,
        }
        results.append(
            {
                "case_id": case.case_id,
                "description": case.description,
                "passed": all(checks.values()),
                "checks": checks,
                "actual": {
                    "status": run.status,
                    "tools": list(actual_tools),
                    "recommendation": run.recommendation.get("action"),
                    "error_categories": error_categories,
                },
            }
        )
    passed = sum(bool(result["passed"]) for result in results)
    return {
        "suite_version": SUITE_VERSION,
        "assistant_version": __version__,
        "case_count": len(results),
        "passed_cases": passed,
        "score": passed / len(results) if results else 0.0,
        "failure_categories": _failure_categories(results),
        "cases": results,
    }


def save_evaluation(report: dict[str, Any], output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "evaluation.json"
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def compare_evaluations(first: dict[str, Any], second: dict[str, Any]) -> dict[str, Any]:
    """Compare two suite reports case by case."""
    first_cases = {case["case_id"]: case for case in first.get("cases", [])}
    second_cases = {case["case_id"]: case for case in second.get("cases", [])}
    ids = sorted(set(first_cases) | set(second_cases))
    return {
        "first_score": first.get("score"),
        "second_score": second.get("score"),
        "score_delta": second.get("score", 0.0) - first.get("score", 0.0),
        "case_changes": [
            {
                "case_id": case_id,
                "first_passed": first_cases.get(case_id, {}).get("passed"),
                "second_passed": second_cases.get(case_id, {}).get("passed"),
            }
            for case_id in ids
        ],
    }


def _failure_categories(results: list[dict[str, Any]]) -> dict[str, int]:
    categories: dict[str, int] = {}
    for result in results:
        if result["passed"]:
            continue
        for name, passed in result["checks"].items():
            if not passed:
                categories[name] = categories.get(name, 0) + 1
    return categories
