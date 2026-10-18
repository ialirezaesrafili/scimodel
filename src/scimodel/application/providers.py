"""Built-in assistant planning providers."""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from scimodel.domain.assistant import PlanStep, TaskRequest


class ProviderPlanError(ValueError):
    """Raised when a provider plan does not match the assistant contract."""


class DeterministicProvider:
    """Safe default provider that returns the tested Phase 1 plan."""

    @property
    def provider_name(self) -> str:
        return "deterministic-rule-planner"

    @property
    def provider_version(self) -> str:
        return "1.0"

    def create_plan(self, request: TaskRequest) -> Sequence[PlanStep]:
        del request
        return (
            PlanStep(
                "inspect",
                "inspect_data",
                "Inspect input quality before modeling.",
                "Input is valid.",
            ),
            PlanStep(
                "validate",
                "validate_model",
                "Fit and validate Michaelis–Menten kinetics.",
                "Validation checks are evaluated.",
            ),
            PlanStep(
                "report",
                "build_report",
                "Write reproducible scientific artifacts.",
                "All required report files exist.",
            ),
        )


class JsonPlanProvider:
    """Controlled adapter for a plan produced by an external model."""

    def __init__(self, plan_path: Path) -> None:
        payload = json.loads(plan_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ProviderPlanError("Provider plan must be a JSON object.")
        self._name = _required_string(payload, "provider")
        self._version = _required_string(payload, "version")
        raw_steps = payload.get("steps")
        if not isinstance(raw_steps, list):
            raise ProviderPlanError("Provider plan must contain a 'steps' list.")
        self._steps = tuple(_parse_step(step) for step in raw_steps)

    @property
    def provider_name(self) -> str:
        return self._name

    @property
    def provider_version(self) -> str:
        return self._version

    def create_plan(self, request: TaskRequest) -> Sequence[PlanStep]:
        del request
        return self._steps


def _required_string(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ProviderPlanError(f"Provider plan field '{key}' must be a non-empty string.")
    return value


def _parse_step(value: Any) -> PlanStep:
    if not isinstance(value, dict):
        raise ProviderPlanError("Each provider plan step must be an object.")
    fields = ("step_id", "tool", "purpose", "verification")
    if any(not isinstance(value.get(field), str) or not value[field].strip() for field in fields):
        raise ProviderPlanError(
            "Each provider step requires non-empty step_id, tool, purpose, and verification."
        )
    return PlanStep(*(value[field] for field in fields))
