"""Domain representation of a general scientific tabular dataset."""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from typing import TypeAlias

import numpy as np
import numpy.typing as npt

from scimodel.domain.formula import RESERVED_NAMES

FloatArray: TypeAlias = npt.NDArray[np.float64]

_UNIT_PATTERNS = (
    re.compile(r"^\s*(?P<name>[^\[]+?)\s*\[(?P<unit>[^\]]+)\]\s*$"),
    re.compile(r"^\s*(?P<name>[^(]+?)\s*\((?P<unit>.+)\)\s*$"),
)


class DatasetError(ValueError):
    """Raised when a dataset cannot support the requested operation."""


def split_label(label: str) -> tuple[str, str | None]:
    """Split a header such as ``temperature [K]`` into its label and unit."""
    for pattern in _UNIT_PATTERNS:
        match = pattern.match(label)
        if match and match.group("name").strip():
            return match.group("name").strip(), match.group("unit").strip()
    return label.strip(), None


def to_identifier(label: str, taken: Iterable[str] = ()) -> str:
    """Return a safe formula identifier for a human column label."""
    name = re.sub(r"[^0-9a-zA-Z_]+", "_", label.strip()).strip("_").lower()
    if not name:
        name = "column"
    if name[0].isdigit():
        name = f"v_{name}"
    if name in RESERVED_NAMES:
        name = f"{name}_"
    existing = set(taken)
    candidate, suffix = name, 2
    while candidate in existing:
        candidate = f"{name}_{suffix}"
        suffix += 1
    return candidate


@dataclass(frozen=True)
class Dataset:
    """A table of named numeric and categorical variables with optional units.

    Missing numeric values are stored as NaN; source values are never altered.
    Column names are safe identifiers so they can be used inside formulas,
    while ``labels`` preserves the original header text.
    """

    name: str
    source: str
    row_count: int
    numeric: dict[str, FloatArray]
    categorical: dict[str, tuple[str, ...]] = field(default_factory=dict)
    units: dict[str, str] = field(default_factory=dict)
    labels: dict[str, str] = field(default_factory=dict)
    column_order: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for column, values in self.numeric.items():
            if values.shape != (self.row_count,):
                raise DatasetError(f"Column '{column}' does not have {self.row_count} rows.")
        for column, text in self.categorical.items():
            if len(text) != self.row_count:
                raise DatasetError(f"Column '{column}' does not have {self.row_count} rows.")

    @property
    def columns(self) -> tuple[str, ...]:
        if self.column_order:
            return self.column_order
        return tuple(self.numeric) + tuple(self.categorical)

    @property
    def numeric_columns(self) -> tuple[str, ...]:
        return tuple(name for name in self.columns if name in self.numeric)

    def label(self, column: str) -> str:
        return self.labels.get(column, column)

    def describe(self, column: str) -> str:
        """Return a readable label including the unit when known."""
        unit = self.units.get(column)
        return f"{self.label(column)} [{unit}]" if unit else self.label(column)

    def require_numeric(self, names: Sequence[str]) -> None:
        missing = [name for name in names if name not in self.numeric]
        if missing:
            available = ", ".join(self.numeric_columns) or "none"
            raise DatasetError(
                f"Column(s) {', '.join(missing)} are not numeric columns. "
                f"Available numeric columns: {available}."
            )

    def complete_mask(self, names: Sequence[str]) -> npt.NDArray[np.bool_]:
        """Return rows where every named numeric column is finite."""
        self.require_numeric(names)
        mask: npt.NDArray[np.bool_] = np.ones(self.row_count, dtype=bool)
        for name in names:
            mask &= np.isfinite(self.numeric[name])
        return mask

    def model_arrays(
        self, target: str, predictors: Sequence[str]
    ) -> tuple[dict[str, FloatArray], FloatArray, int]:
        """Return complete-case predictor arrays, target array, and dropped row count."""
        if target in predictors:
            raise DatasetError("The target cannot also be a predictor.")
        if not predictors:
            raise DatasetError("At least one predictor column is required.")
        mask = self.complete_mask([target, *predictors])
        variables = {name: self.numeric[name][mask] for name in predictors}
        return variables, self.numeric[target][mask], int(self.row_count - mask.sum())
