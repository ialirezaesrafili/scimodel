"""Domain objects for deterministic tabular-data inspection."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

Severity = Literal["info", "warning", "error"]


@dataclass(frozen=True)
class DataIssue:
    """A machine-readable data-quality finding."""

    code: str
    severity: Severity
    message: str
    column: str | None = None


@dataclass(frozen=True)
class ColumnProfile:
    """Summary statistics for one column."""

    name: str
    non_empty: int
    missing: int
    numeric: bool
    distinct: int
    minimum: float | None = None
    maximum: float | None = None
    mean: float | None = None


@dataclass(frozen=True)
class DataInspectionReport:
    """Complete result of inspecting one tabular input."""

    source: str
    row_count: int
    column_count: int
    columns: tuple[ColumnProfile, ...]
    duplicate_rows: int
    issues: tuple[DataIssue, ...] = field(default_factory=tuple)

    @property
    def valid(self) -> bool:
        """Return whether no blocking data-quality errors were found."""
        return not any(issue.severity == "error" for issue in self.issues)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation of the report."""
        result = asdict(self)
        result["valid"] = self.valid
        return result
