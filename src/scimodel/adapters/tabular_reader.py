"""Read common scientific table formats into a :class:`Dataset`.

Supported without extra dependencies: CSV, TSV, whitespace/semicolon-delimited
text (``.txt``, ``.dat``), and JSON record lists. Excel (``.xlsx``) uses the
optional ``openpyxl`` package and Parquet the optional ``pandas`` package.
"""

from __future__ import annotations

import csv
import io
import json
import math
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import numpy as np

from scimodel.domain.dataset import Dataset, split_label, to_identifier

SUPPORTED_SUFFIXES = frozenset({".csv", ".tsv", ".txt", ".dat", ".json", ".xlsx", ".parquet"})
_MISSING_TOKENS = frozenset({"", "na", "n/a", "nan", "null", "none", "-", "--", "?"})


class TableReadError(ValueError):
    """Raised when a file cannot be read as a scientific table."""


def read_table(path: Path, *, max_bytes: int = 200_000_000) -> Dataset:
    """Read one supported file without modifying its source values."""
    if not path.is_file():
        raise TableReadError(f"Input file does not exist: {path}")
    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        supported = ", ".join(sorted(SUPPORTED_SUFFIXES))
        raise TableReadError(f"Unsupported file type '{suffix}'. Supported: {supported}.")
    if path.stat().st_size > max_bytes:
        raise TableReadError(f"Input file is larger than the {max_bytes} byte safety limit.")

    if suffix == ".json":
        headers, rows = _read_json(path)
    elif suffix == ".xlsx":
        headers, rows = _read_xlsx(path)
    elif suffix == ".parquet":
        headers, rows = _read_parquet(path)
    else:
        headers, rows = _read_delimited(path, suffix)
    return build_dataset(path.stem, str(path), headers, rows)


def build_dataset(
    name: str, source: str, headers: Sequence[str], rows: Sequence[Sequence[str]]
) -> Dataset:
    """Classify raw string columns into numeric and categorical variables."""
    if not headers:
        raise TableReadError("The table has no header row.")
    if not rows:
        raise TableReadError("The table contains no data rows.")

    identifiers: list[str] = []
    labels: dict[str, str] = {}
    units: dict[str, str] = {}
    for header in headers:
        label, unit = split_label(str(header))
        identifier = to_identifier(label or "column", identifiers)
        identifiers.append(identifier)
        labels[identifier] = label or identifier
        if unit:
            units[identifier] = unit

    numeric: dict[str, Any] = {}
    categorical: dict[str, tuple[str, ...]] = {}
    for index, identifier in enumerate(identifiers):
        raw = [row[index].strip() if index < len(row) else "" for row in rows]
        parsed = [_parse_number(value) for value in raw]
        present = [value for value, number in zip(raw, parsed, strict=True) if not _missing(value)]
        if present and all(
            number is not None
            for value, number in zip(raw, parsed, strict=True)
            if not _missing(value)
        ):
            numeric[identifier] = np.array(
                [math.nan if number is None else number for number in parsed], dtype=np.float64
            )
        else:
            categorical[identifier] = tuple(raw)

    return Dataset(
        name=name,
        source=source,
        row_count=len(rows),
        numeric=numeric,
        categorical=categorical,
        units=units,
        labels=labels,
        column_order=tuple(identifiers),
    )


def _missing(value: str) -> bool:
    return value.strip().lower() in _MISSING_TOKENS


def _parse_number(value: str) -> float | None:
    if _missing(value):
        return None
    cleaned = value.strip().replace("−", "-")
    try:
        number = float(cleaned)
    except ValueError:
        # Accept a decimal comma (common in European lab exports) when unambiguous.
        if cleaned.count(",") == 1 and "." not in cleaned:
            try:
                number = float(cleaned.replace(",", "."))
            except ValueError:
                return None
        else:
            return None
    return number if math.isfinite(number) else None


def _read_delimited(path: Path, suffix: str) -> tuple[list[str], list[list[str]]]:
    try:
        text = path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        text = path.read_text(encoding="latin-1")
    lines = [
        line
        for line in text.splitlines()
        if line.strip() and not line.lstrip().startswith(("#", "%", "//"))
    ]
    if not lines:
        raise TableReadError(f"The file contains no table: {path}")

    sample = "\n".join(lines[:50])
    delimiter: str | None
    if suffix == ".tsv":
        delimiter = "\t"
    elif suffix == ".csv":
        delimiter = _sniff(sample, default=",")
    else:
        delimiter = _sniff(sample, default=None)

    if delimiter is None:
        records = [line.split() for line in lines]
    else:
        reader = csv.reader(io.StringIO("\n".join(lines)), delimiter=delimiter)
        try:
            records = [list(record) for record in reader]
        except csv.Error as exc:
            raise TableReadError(f"Table parsing failed for {path}: {exc}") from exc

    headers = [cell.strip() for cell in records[0]]
    if not all(headers):
        raise TableReadError("The header contains an empty column name.")
    if len(set(headers)) != len(headers):
        raise TableReadError("The header contains duplicate column names.")
    body = records[1:]
    for line_number, record in enumerate(body, start=2):
        if len(record) > len(headers):
            raise TableReadError(f"Row {line_number} has more values than headers.")
    return headers, body


def _sniff(sample: str, *, default: str | None) -> str | None:
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
        return dialect.delimiter
    except csv.Error:
        return default


def _read_json(path: Path) -> tuple[list[str], list[list[str]]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise TableReadError(f"Invalid JSON in {path}: {exc}") from exc
    if isinstance(payload, dict) and isinstance(payload.get("data"), list):
        payload = payload["data"]
    if isinstance(payload, dict) and all(isinstance(value, list) for value in payload.values()):
        headers = [str(key) for key in payload]
        length = max((len(value) for value in payload.values()), default=0)
        rows = [
            [_cell(payload[key][i]) if i < len(payload[key]) else "" for key in payload]
            for i in range(length)
        ]
        return headers, rows
    if not isinstance(payload, list) or not all(isinstance(item, dict) for item in payload):
        raise TableReadError("JSON input must be a list of records or a mapping of columns.")
    headers = []
    for record in payload:
        for key in record:
            if str(key) not in headers:
                headers.append(str(key))
    rows = [[_cell(record.get(key)) for key in headers] for record in payload]
    return headers, rows


def _read_xlsx(path: Path) -> tuple[list[str], list[list[str]]]:
    try:
        import openpyxl
    except ImportError as exc:
        raise TableReadError(
            "Reading Excel files requires the optional dependency: pip install 'scimodel[excel]'"
        ) from exc
    workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
    sheet = workbook.active
    if sheet is None:
        raise TableReadError(f"The workbook has no active sheet: {path}")
    records = [[_cell(value) for value in row] for row in sheet.iter_rows(values_only=True)]
    records = [record for record in records if any(cell.strip() for cell in record)]
    if not records:
        raise TableReadError(f"The workbook sheet is empty: {path}")
    return [cell.strip() for cell in records[0]], records[1:]


def _read_parquet(path: Path) -> tuple[list[str], list[list[str]]]:
    try:
        import pandas as pd
    except ImportError as exc:
        raise TableReadError(
            "Reading Parquet files requires pandas and pyarrow: pip install pandas pyarrow"
        ) from exc
    frame = pd.read_parquet(path)
    headers = [str(column) for column in frame.columns]
    rows = [[_cell(value) for value in row] for row in frame.itertuples(index=False)]
    return headers, rows


def _cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and not math.isfinite(value):
        return ""
    return str(value)
