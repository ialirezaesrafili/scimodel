"""Profile any scientific dataset: column roles, quality issues, and relationship shapes."""

from __future__ import annotations

import math
import re
from dataclasses import asdict, dataclass, field
from typing import Any, TypeAlias

import numpy as np
import numpy.typing as npt

from scimodel.adapters.scipy_statistics import pearson, skewness, spearman
from scimodel.domain.dataset import Dataset

FloatArray: TypeAlias = npt.NDArray[np.float64]

_INDEX_NAMES = re.compile(
    r"^(id|index|idx|run|run_id|sample|sample_id|replicate|rep|well|trial|subject|batch|plate|"
    r"row|obs|observation|no|n|number)(_.*)?$"
)
_TARGET_TOKENS = frozenset(
    {
        "rate",
        "velocity",
        "response",
        "yield",
        "signal",
        "intensity",
        "output",
        "od",
        "od600",
        "absorbance",
        "activity",
        "growth",
        "strength",
        "stress",
        "current",
        "voltage",
        "flux",
        "efficiency",
        "conversion",
        "period",
        "displacement",
        "y",
        "concentration_out",
        "viscosity",
        "conductivity",
        "survival",
        "inhibition",
    }
)
_TIME_HINTS = re.compile(r"^(t|time|times|hours?|h|minutes?|min|seconds?|s|day|days|age)(_.*)?$")
_TEMPERATURE_HINTS = re.compile(r"(temp|temperature|^t_k$|kelvin)")


@dataclass(frozen=True)
class ColumnSummary:
    name: str
    label: str
    unit: str | None
    kind: str
    count: int
    missing: int
    distinct: int
    role: str
    minimum: float | None = None
    maximum: float | None = None
    mean: float | None = None
    std: float | None = None
    skewness: float | None = None
    outliers: int = 0
    all_positive: bool = False
    integer_valued: bool = False


@dataclass(frozen=True)
class RelationshipSummary:
    """How a candidate target varies with one predictor."""

    predictor: str
    target: str
    pearson: float
    spearman: float
    hints: tuple[str, ...]
    scores: dict[str, float]


@dataclass(frozen=True)
class DataIssueSummary:
    severity: str
    code: str
    message: str
    column: str | None = None


@dataclass(frozen=True)
class DatasetProfile:
    dataset: str
    source: str
    rows: int
    columns: tuple[ColumnSummary, ...]
    target: str | None
    predictors: tuple[str, ...]
    relationships: tuple[RelationshipSummary, ...]
    issues: tuple[DataIssueSummary, ...]
    replicated_predictor_levels: int = 0
    notes: tuple[str, ...] = field(default_factory=tuple)

    def column(self, name: str) -> ColumnSummary | None:
        return next((column for column in self.columns if column.name == name), None)

    def relationship(self, predictor: str) -> RelationshipSummary | None:
        return next((item for item in self.relationships if item.predictor == predictor), None)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def profile_dataset(
    dataset: Dataset, *, target: str | None = None, predictors: tuple[str, ...] | None = None
) -> DatasetProfile:
    """Return a deterministic profile without changing any source value."""
    columns = tuple(_summarize(dataset, name) for name in dataset.columns)
    issues: list[DataIssueSummary] = []
    for column in columns:
        if column.missing:
            issues.append(
                DataIssueSummary(
                    "warning",
                    "missing_values",
                    f"{column.missing} missing value(s); affected rows are excluded from fits.",
                    column.name,
                )
            )
        if column.kind == "numeric" and column.distinct == 1:
            issues.append(
                DataIssueSummary(
                    "info",
                    "constant_column",
                    "Column is constant; it cannot explain variation.",
                    column.name,
                )
            )
        if column.outliers:
            issues.append(
                DataIssueSummary(
                    "warning",
                    "possible_outliers",
                    f"{column.outliers} value(s) lie more than 4 robust SDs from the median.",
                    column.name,
                )
            )

    chosen_target = target or _guess_target(columns)
    chosen_predictors = predictors or _guess_predictors(columns, chosen_target)
    relationships: list[RelationshipSummary] = []
    replicated = 0
    if chosen_target and chosen_target in dataset.numeric:
        for predictor in chosen_predictors:
            if predictor not in dataset.numeric:
                continue
            relationships.append(_relationship(dataset, predictor, chosen_target))
        if chosen_predictors:
            mask = dataset.complete_mask([chosen_target, *chosen_predictors])
            keys = np.column_stack([dataset.numeric[p][mask] for p in chosen_predictors])
            _, counts = np.unique(keys, axis=0, return_counts=True)
            replicated = int(np.sum(counts > 1))

    row_count = dataset.row_count
    if row_count < 10:
        issues.append(
            DataIssueSummary(
                "warning",
                "small_sample",
                f"Only {row_count} rows: complex models cannot be distinguished reliably.",
            )
        )
    notes: list[str] = []
    if replicated:
        notes.append(
            f"{replicated} predictor setting(s) are replicated, enabling a pure-error "
            "lack-of-fit test."
        )
    return DatasetProfile(
        dataset=dataset.name,
        source=dataset.source,
        rows=row_count,
        columns=columns,
        target=chosen_target,
        predictors=tuple(chosen_predictors),
        relationships=tuple(relationships),
        issues=tuple(issues),
        replicated_predictor_levels=replicated,
        notes=tuple(notes),
    )


def _summarize(dataset: Dataset, name: str) -> ColumnSummary:
    if name in dataset.categorical:
        values = dataset.categorical[name]
        present = [value for value in values if value.strip()]
        return ColumnSummary(
            name=name,
            label=dataset.label(name),
            unit=dataset.units.get(name),
            kind="categorical",
            count=len(present),
            missing=len(values) - len(present),
            distinct=len(set(present)),
            role="grouping" if 1 < len(set(present)) < max(2, len(values)) else "label",
        )
    values = dataset.numeric[name]
    finite = values[np.isfinite(values)]
    integer_valued = bool(len(finite)) and bool(np.all(np.equal(np.mod(finite, 1), 0)))
    median = float(np.median(finite)) if len(finite) else 0.0
    mad = float(np.median(np.abs(finite - median))) * 1.4826 if len(finite) else 0.0
    outliers = int(np.sum(np.abs(finite - median) > 4 * mad)) if mad > 0 else 0
    role = _numeric_role(name, finite, integer_valued)
    return ColumnSummary(
        name=name,
        label=dataset.label(name),
        unit=dataset.units.get(name),
        kind="numeric",
        count=len(finite),
        missing=int(len(values) - len(finite)),
        distinct=len(np.unique(finite)),
        role=role,
        minimum=float(finite.min()) if len(finite) else None,
        maximum=float(finite.max()) if len(finite) else None,
        mean=float(finite.mean()) if len(finite) else None,
        std=float(finite.std(ddof=1)) if len(finite) > 1 else None,
        skewness=skewness(finite) if len(finite) > 2 else None,
        outliers=outliers if role != "index" else 0,
        all_positive=bool(len(finite)) and bool(np.all(finite > 0)),
        integer_valued=integer_valued,
    )


def _numeric_role(name: str, values: FloatArray, integer_valued: bool) -> str:
    if len(values) and np.ptp(values) == 0:
        return "constant"
    if _TIME_HINTS.match(name):
        return "time"
    if _INDEX_NAMES.match(name):
        return "index"
    if (
        integer_valued
        and len(values) > 5
        and len(np.unique(values)) == len(values)
        and np.all(np.diff(values) == 1)
    ):
        return "index"
    if _TEMPERATURE_HINTS.search(name):
        return "temperature"
    return "measurement"


def _guess_target(columns: tuple[ColumnSummary, ...]) -> str | None:
    usable = [c for c in columns if c.kind == "numeric" and c.role not in ("index", "constant")]
    if len(usable) < 2:
        return usable[0].name if usable else None
    for column in usable:
        tokens = set(column.name.lower().split("_"))
        if tokens & _TARGET_TOKENS and column.role not in ("time", "temperature"):
            return column.name
    # Default convention: the last measured column is the response.
    for column in reversed(usable):
        if column.role == "measurement":
            return column.name
    return usable[-1].name


def _guess_predictors(columns: tuple[ColumnSummary, ...], target: str | None) -> tuple[str, ...]:
    return tuple(
        column.name
        for column in columns
        if column.kind == "numeric"
        and column.name != target
        and column.role not in ("index", "constant")
    )


def _relationship(dataset: Dataset, predictor: str, target: str) -> RelationshipSummary:
    mask = dataset.complete_mask([predictor, target])
    x, y = dataset.numeric[predictor][mask], dataset.numeric[target][mask]
    rho, _ = spearman(x, y)
    r = pearson(x, y)
    scores: dict[str, float] = {}
    hints: list[str] = []
    if len(x) < 4 or np.ptp(x) == 0:
        return RelationshipSummary(predictor, target, r, rho, ("insufficient_variation",), scores)

    # Average replicates so shape tests describe the mean response.
    levels, inverse = np.unique(x, return_inverse=True)
    means = np.bincount(inverse, weights=y) / np.bincount(inverse)
    scores["linear_r2"] = _r2(levels, means)
    if np.all(levels > 0) and np.all(means > 0):
        scores["power_law_r2"] = _r2(np.log(levels), np.log(means))
    if np.all(means > 0):
        scores["exponential_r2"] = _r2(levels, np.log(means))
    if np.all(levels > 0):
        scores["logarithmic_r2"] = _r2(np.log(levels), means)
        scores["reciprocal_r2"] = _r2(1.0 / levels, means)

    if abs(rho) > 0.9:
        hints.append("monotonic_increasing" if rho > 0 else "monotonic_decreasing")
    if len(levels) >= 6:
        third = len(levels) // 3
        start_slope = _slope(levels[: third + 1], means[: third + 1])
        end_slope = _slope(levels[-third - 1 :], means[-third - 1 :])
        if (
            abs(rho) > 0.8
            and start_slope != 0
            and np.sign(start_slope) == np.sign(end_slope)
            and abs(end_slope) < 0.3 * abs(start_slope)
        ):
            hints.append("saturating")
        if abs(rho) > 0.8 and abs(start_slope) < 0.3 * abs(end_slope):
            hints.append("accelerating")
        smooth = _smooth(means)
        turns = int(np.count_nonzero(np.diff(np.sign(np.diff(smooth))) != 0))
        span = float(np.ptp(smooth)) or 1.0
        if turns <= 2:
            for extreme, sign in ((int(np.argmax(smooth)), 1.0), (int(np.argmin(smooth)), -1.0)):
                if 0 < extreme < len(smooth) - 1:
                    left = sign * (smooth[extreme] - smooth[0]) / span
                    right = sign * (smooth[extreme] - smooth[-1]) / span
                    if left > 0.3 and right > 0.3:
                        hints.append("peak" if sign > 0 else "valley")
        if _is_sigmoid(levels, means):
            hints.append("sigmoidal")
        periodic_score = _periodicity(levels, means)
        scores["periodicity"] = periodic_score
        detrended = smooth - np.polyval(np.polyfit(levels, smooth, 2), levels)
        crossings = int(np.count_nonzero(np.diff(np.sign(detrended)) != 0))
        dominance = float(np.std(detrended) / (np.std(means) or 1.0))
        centered = detrended - detrended.mean()
        denominator = float(np.sum(centered**2)) or 1.0
        autocorrelation = float(np.sum(centered[1:] * centered[:-1]) / denominator)
        scores["oscillation_crossings"] = float(crossings)
        scores["lag1_autocorrelation"] = autocorrelation
        if crossings >= 4 and dominance > 0.5 and autocorrelation > 0.5 and abs(rho) < 0.8:
            hints.append("oscillating")
    if scores.get("power_law_r2", 0) > max(0.98, scores["linear_r2"] + 0.01):
        hints.append("power_law_like")
    if scores.get("exponential_r2", 0) > max(0.98, scores["linear_r2"] + 0.01):
        hints.append("exponential_like")
    if scores["linear_r2"] > 0.98:
        hints.append("linear_like")
    if abs(rho) < 0.2 and not any(h in hints for h in ("peak", "valley", "oscillating")):
        hints.append("weak_relationship")
    return RelationshipSummary(predictor, target, r, rho, tuple(dict.fromkeys(hints)), scores)


def _r2(x: FloatArray, y: FloatArray) -> float:
    if len(x) < 3 or np.ptp(x) == 0 or np.ptp(y) == 0:
        return 0.0
    coefficients = np.polyfit(x, y, 1)
    residual = y - np.polyval(coefficients, x)
    return float(1.0 - np.sum(residual**2) / np.sum((y - y.mean()) ** 2))


def _smooth(values: FloatArray) -> FloatArray:
    """Centered moving average that preserves length (edges use shorter windows)."""
    window = max(1, len(values) // 40)
    if window == 1:
        return values.astype(np.float64)
    kernel = np.ones(2 * window + 1)
    sums = np.convolve(values, kernel, mode="same")
    counts = np.convolve(np.ones_like(values), kernel, mode="same")
    return np.asarray(sums / counts, dtype=np.float64)


def _poly_r2(x: FloatArray, y: FloatArray, degree: int) -> float:
    if len(x) <= degree + 1 or np.ptp(y) == 0:
        return 0.0
    residual = y - np.polyval(np.polyfit(x, y, degree), x)
    return float(1.0 - np.sum(residual**2) / np.sum((y - y.mean()) ** 2))


def _slope(x: FloatArray, y: FloatArray) -> float:
    if len(x) < 2 or np.ptp(x) == 0:
        return 0.0
    return float(np.polyfit(x, y, 1)[0])


def _is_sigmoid(x: FloatArray, y: FloatArray) -> bool:
    if len(x) < 8:
        return False
    span = float(np.ptp(y))
    if span == 0:
        return False
    normalized = (y - y.min()) / span
    increasing = normalized[-1] > normalized[0]
    if not increasing:
        normalized = 1.0 - normalized
    slopes = np.diff(normalized) / np.diff(x)
    if not np.all(np.isfinite(slopes)):
        return False
    steepest = int(np.argmax(slopes))
    lower_flat = float(np.mean(normalized[: max(2, len(x) // 6)])) < 0.15
    upper_flat = float(np.mean(normalized[-max(2, len(x) // 6) :])) > 0.85
    return 0 < steepest < len(slopes) - 1 and lower_flat and upper_flat


def _periodicity(x: FloatArray, y: FloatArray) -> float:
    """Fraction of detrended variance in the dominant Fourier component (uniform resample)."""
    if len(x) < 12:
        return 0.0
    grid = np.linspace(x.min(), x.max(), len(x))
    values = np.interp(grid, x, y)
    trend = np.polyval(np.polyfit(grid, values, 2), grid)
    detrended = values - trend
    power = np.abs(np.fft.rfft(detrended)) ** 2
    if len(power) < 3 or float(power[1:].sum()) == 0.0:
        return 0.0
    dominant = float(power[1:].max())
    cycles = int(np.argmax(power[1:])) + 1
    if cycles < 2:
        return 0.0
    return float(dominant / power[1:].sum()) * min(1.0, math.log2(cycles + 1) / 2)


def dominant_frequency(x: FloatArray, y: FloatArray) -> float:
    """Return the dominant angular frequency of y(x), used to seed periodic models."""
    order = np.argsort(x)
    xs, ys = x[order], y[order]
    if len(xs) < 4 or np.ptp(xs) == 0:
        return 1.0
    grid = np.linspace(xs.min(), xs.max(), max(len(xs), 64))
    values = np.interp(grid, xs, ys)
    values = values - np.polyval(np.polyfit(grid, values, 1), grid)
    spectrum = np.abs(np.fft.rfft(values))
    frequencies = np.fft.rfftfreq(len(grid), d=float(grid[1] - grid[0]))
    if len(spectrum) < 2:
        return 1.0
    index = int(np.argmax(spectrum[1:])) + 1
    return float(2 * np.pi * frequencies[index])
