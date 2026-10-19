"""Contracts for the transparent assistant workflow."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class TaskRequest:
    """User-supplied objective and input reference."""

    objective: str
    input_path: str
    x_column: str = "substrate_conc"
    y_column: str = "reaction_velocity"


@dataclass(frozen=True)
class ContextItem:
    """Reviewable personal or project context used by an assistant run."""

    key: str
    kind: str
    value: str
    source: str
    confidence: str
    status: str
    updated_at: str


@dataclass(frozen=True)
class PlanStep:
    """One planned operation with its verification requirement."""

    step_id: str
    tool: str
    purpose: str
    verification: str


@dataclass(frozen=True)
class ToolSchema:
    """Versioned public contract for an assistant tool."""

    name: str
    version: str
    description: str
    input_fields: tuple[str, ...]
    output_fields: tuple[str, ...]
    requires_approval: bool = False


@dataclass(frozen=True)
class ToolCallRecord:
    """Evidence that a registered tool was actually called."""

    tool: str
    tool_version: str
    input: dict[str, Any]
    status: str
    output: dict[str, Any]
    error: str | None = None
    error_category: str | None = None


@dataclass(frozen=True)
class VerificationResult:
    """Outcome of checking the assistant workflow."""

    passed: bool
    checks: tuple[dict[str, Any], ...]


@dataclass(frozen=True)
class AssistantRun:
    """Complete, serializable record of one assistant execution."""

    request: TaskRequest
    plan: tuple[PlanStep, ...]
    tool_calls: tuple[ToolCallRecord, ...]
    verification: VerificationResult
    status: str
    recommendation: dict[str, Any]
    provider: dict[str, Any] | None = None
    approvals: tuple[dict[str, Any], ...] = ()
    context: tuple[dict[str, Any], ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
