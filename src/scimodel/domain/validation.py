"""Domain objects for model validation results."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class ValidationCheck:
    """One explicit validation assertion."""

    name: str
    passed: bool
    message: str
    value: float | bool | int | str | None = None


@dataclass(frozen=True)
class ValidationResult:
    """Validation outcome for one fitted model and dataset."""

    source: str
    model: str
    data_quality: dict[str, int]
    diagnostics: dict[str, float | bool | int]
    checks: tuple[ValidationCheck, ...]
    assumptions: tuple[str, ...]
    limitations: tuple[str, ...]
    warnings: tuple[str, ...] = field(default_factory=tuple)

    @property
    def valid(self) -> bool:
        """Return whether every required validation check passed."""
        return all(check.passed for check in self.checks)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation."""
        result = asdict(self)
        result["valid"] = self.valid
        return result
