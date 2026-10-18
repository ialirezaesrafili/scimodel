"""Edge-case tests for safe CSV inspection."""

from pathlib import Path

import pytest

from scimodel.adapters.csv_reader import CsvReadError
from scimodel.application.inspect_data import inspect_csv


def test_empty_csv_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "empty.csv"
    path.write_text("", encoding="utf-8")

    with pytest.raises(CsvReadError, match="empty or has no header"):
        inspect_csv(path)


def test_duplicate_headers_are_rejected(tmp_path: Path) -> None:
    path = tmp_path / "duplicate_headers.csv"
    path.write_text("substrate_conc,substrate_conc\n0.1,0.2\n", encoding="utf-8")

    with pytest.raises(CsvReadError, match="duplicate column names"):
        inspect_csv(path)


def test_extra_values_are_rejected(tmp_path: Path) -> None:
    path = tmp_path / "extra_values.csv"
    path.write_text("substrate_conc,reaction_velocity\n0.1,10,unexpected\n", encoding="utf-8")

    with pytest.raises(CsvReadError, match="more values than headers"):
        inspect_csv(path)


def test_missing_values_are_reported_without_silent_imputation(tmp_path: Path) -> None:
    path = tmp_path / "missing.csv"
    path.write_text(
        "substrate_conc,reaction_velocity\n0.1,10\n0.2,\n0.3,30\n0.4,40\n",
        encoding="utf-8",
    )

    report = inspect_csv(path)
    assert not report.valid
    assert any(issue.code == "missing_values" for issue in report.issues)
    assert any(issue.code == "non_numeric_value" for issue in report.issues)


def test_missing_file_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(CsvReadError, match="does not exist"):
        inspect_csv(tmp_path / "does-not-exist.csv")


def test_whitespace_around_headers_is_normalized(tmp_path: Path) -> None:
    path = tmp_path / "whitespace_headers.csv"
    path.write_text(
        " substrate_conc , reaction_velocity \n0.1,10\n0.2,20\n0.3,30\n0.4,40\n",
        encoding="utf-8",
    )

    report = inspect_csv(path)
    assert report.valid
    assert {column.name for column in report.columns} == {
        "substrate_conc",
        "reaction_velocity",
    }
