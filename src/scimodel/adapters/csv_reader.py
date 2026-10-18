"""CSV input adapter for the application layer."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path


class CsvReadError(ValueError):
    """Raised when a CSV file cannot be read as a tabular input."""


@dataclass(frozen=True)
class CsvTable:
    """A small, dependency-free tabular representation."""

    headers: tuple[str, ...]
    rows: tuple[dict[str, str], ...]


def read_csv(path: Path, *, encoding: str = "utf-8", delimiter: str = ",") -> CsvTable:
    """Read a CSV file without modifying its values."""
    if not path.is_file():
        raise CsvReadError(f"Input file does not exist: {path}")

    try:
        with path.open("r", encoding=encoding, newline="") as handle:
            reader = csv.DictReader(handle, delimiter=delimiter)
            if reader.fieldnames is None:
                raise CsvReadError("CSV input is empty or has no header row")

            original_headers = tuple(reader.fieldnames)
            headers = tuple(header.strip() for header in original_headers)
            if not all(headers):
                raise CsvReadError("CSV header contains an empty column name")
            if len(set(headers)) != len(headers):
                raise CsvReadError("CSV header contains duplicate column names")

            rows: list[dict[str, str]] = []
            for line_number, row in enumerate(reader, start=2):
                if None in row:
                    raise CsvReadError(f"CSV row {line_number} has more values than headers")
                rows.append(
                    {
                        header: (row.get(original_header) or "").strip()
                        for original_header, header in zip(original_headers, headers, strict=True)
                    }
                )
    except UnicodeDecodeError as exc:
        raise CsvReadError(f"CSV input is not valid {encoding}: {path}") from exc
    except csv.Error as exc:
        raise CsvReadError(f"CSV parsing failed for {path}: {exc}") from exc

    return CsvTable(headers=headers, rows=tuple(rows))
