"""Tests for the multi-format table reader and dataset domain object."""

import json
from pathlib import Path

import numpy as np
import pytest

from scimodel.adapters.tabular_reader import TableReadError, build_dataset, read_table
from scimodel.domain.dataset import Dataset, DatasetError, split_label, to_identifier


@pytest.mark.parametrize(
    ("label", "expected"),
    [
        ("temperature [K]", ("temperature", "K")),
        ("rate [mmol/(g*h)]", ("rate", "mmol/(g*h)")),
        ("time (s)", ("time", "s")),
        ("plain", ("plain", None)),
        ("[K]", ("[K]", None)),
    ],
)
def test_split_label(label: str, expected: tuple[str, str | None]) -> None:
    assert split_label(label) == expected


def test_to_identifier_is_safe_and_unique() -> None:
    assert to_identifier("Catalyst loading (%)") == "catalyst_loading"
    assert to_identifier("2nd run") == "v_2nd_run"
    assert to_identifier("exp") == "exp_"
    assert to_identifier("x", ["x", "x_2"]) == "x_3"
    assert to_identifier("!!!") == "column"


def test_read_csv_with_units_missing_and_text(tmp_path: Path) -> None:
    path = tmp_path / "lab.csv"
    path.write_text(
        "# exported by instrument\nsample,temperature [K],rate\nA,300,1.5\nB,310,NA\nC,320,2.5\n",
        encoding="utf-8",
    )
    dataset = read_table(path)
    assert dataset.numeric_columns == ("temperature", "rate")
    assert dataset.units == {"temperature": "K"}
    assert dataset.categorical["sample"] == ("A", "B", "C")
    assert np.isnan(dataset.numeric["rate"][1])
    assert dataset.describe("temperature") == "temperature [K]"
    variables, y, dropped = dataset.model_arrays("rate", ["temperature"])
    assert dropped == 1 and list(y) == [1.5, 2.5] and list(variables["temperature"]) == [300, 320]


def test_semicolon_decimal_comma_and_whitespace(tmp_path: Path) -> None:
    semicolon = tmp_path / "eu.txt"
    semicolon.write_text("x;y\n1,5;2,0\n2,5;3,0\n3,5;4,5\n", encoding="utf-8")
    assert list(read_table(semicolon).numeric["x"]) == [1.5, 2.5, 3.5]
    spaces = tmp_path / "plain.dat"
    spaces.write_text("t   v\n0   1.0\n1   2.0\n2   4.1\n", encoding="utf-8")
    assert read_table(spaces).numeric_columns == ("t", "v")
    tsv = tmp_path / "table.tsv"
    tsv.write_text("a\tb\n1\t2\n3\t4\n", encoding="utf-8")
    assert read_table(tsv).row_count == 2


def test_json_records_and_columns(tmp_path: Path) -> None:
    records = tmp_path / "records.json"
    records.write_text(json.dumps([{"x": 1, "y": 2.0}, {"x": 2, "y": None, "z": "a"}]))
    dataset = read_table(records)
    assert dataset.columns == ("x", "y", "z") and np.isnan(dataset.numeric["y"][1])
    columns = tmp_path / "columns.json"
    columns.write_text(json.dumps({"data": {"x": [1, 2, 3], "y": [2, 4, 6]}}))
    with pytest.raises(TableReadError):
        read_table(columns)  # "data" must hold records
    columns.write_text(json.dumps({"x": [1, 2, 3], "y": [2, 4, 6]}))
    assert read_table(columns).row_count == 3
    bad = tmp_path / "bad.json"
    bad.write_text("{nope")
    with pytest.raises(TableReadError, match="Invalid JSON"):
        read_table(bad)
    scalar = tmp_path / "scalar.json"
    scalar.write_text("3")
    with pytest.raises(TableReadError, match="list of records"):
        read_table(scalar)


def test_xlsx(tmp_path: Path) -> None:
    openpyxl = pytest.importorskip("openpyxl")
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.append(["dose [mg]", "response"])
    for dose, response in ((1, 0.1), (2, 0.3), (4, 0.6)):
        sheet.append([dose, response])
    path = tmp_path / "plate.xlsx"
    workbook.save(path)
    dataset = read_table(path)
    assert dataset.units == {"dose": "mg"} and list(dataset.numeric["response"]) == [0.1, 0.3, 0.6]


@pytest.mark.parametrize(
    ("content", "suffix", "message"),
    [
        ("", ".csv", "no table"),
        ("x,y\n", ".csv", "no data rows"),
        ("x,x\n1,2\n", ".csv", "duplicate"),
        ("x,\n1,2\n", ".csv", "empty column"),
        ("x,y\n1,2,3\n", ".csv", "more values"),
        ("x,y\n1,2\n", ".pdf", "Unsupported"),
    ],
)
def test_read_errors(tmp_path: Path, content: str, suffix: str, message: str) -> None:
    path = tmp_path / f"bad{suffix}"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(TableReadError, match=message):
        read_table(path)


def test_missing_and_oversized_files(tmp_path: Path) -> None:
    with pytest.raises(TableReadError, match="does not exist"):
        read_table(tmp_path / "missing.csv")
    path = tmp_path / "big.csv"
    path.write_text("x,y\n1,2\n")
    with pytest.raises(TableReadError, match="safety limit"):
        read_table(path, max_bytes=3)


def test_latin1_fallback(tmp_path: Path) -> None:
    path = tmp_path / "latin.csv"
    path.write_bytes("temp [°C],y\n1,2\n2,3\n".encode("latin-1"))
    assert read_table(path).units == {"temp": "°C"}


def test_dataset_validation_errors() -> None:
    with pytest.raises(DatasetError, match="rows"):
        Dataset("d", "s", 2, {"x": np.array([1.0])})
    with pytest.raises(DatasetError, match="rows"):
        Dataset("d", "s", 2, {}, categorical={"c": ("a",)})
    dataset = build_dataset("d", "s", ["x", "y"], [["1", "2"], ["2", "4"]])
    with pytest.raises(DatasetError, match="not numeric"):
        dataset.require_numeric(["z"])
    with pytest.raises(DatasetError, match="cannot also"):
        dataset.model_arrays("x", ["x"])
    with pytest.raises(DatasetError, match="At least one predictor"):
        dataset.model_arrays("x", [])
    with pytest.raises(TableReadError):
        build_dataset("d", "s", [], [])
