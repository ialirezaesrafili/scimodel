"""Provider boundary for assistant planning."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from scimodel.domain.assistant import PlanStep, TaskRequest


class AssistantProvider(Protocol):
    """Interface a hosted or local language model can implement later."""

    @property
    def provider_name(self) -> str:
        """Return a stable provider identifier."""

    @property
    def provider_version(self) -> str:
        """Return the provider contract version."""

    def create_plan(self, request: TaskRequest) -> Sequence[PlanStep]:
        """Create a plan without executing tools."""
