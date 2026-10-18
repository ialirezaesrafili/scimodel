"""Integration tests for the Phase 2 CSV inspection workflow."""

import json
from pathlib import Path

from scimodel.application.inspect_data import inspect_csv
from scimodel.interfaces.cli import main

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PUROMYCIN_CSV = PROJECT_ROOT / "examples" / "enzyme_kinetics_puromycin.csv"


def test_puromycin_csv_is_valid_and_profiled() -> None:
    report = inspect_csv(PUROMYCIN_CSV)

    assert report.valid
    assert report.row_count == 12
    assert report.column_count == 2
    assert report.duplicate_rows == 0
    assert {column.name for column in report.columns} == {
        "substrate_conc",
        "reaction_velocity",
    }
    assert not [issue for issue in report.issues if issue.severity == "error"]


def test_cli_data_inspect_outputs_json(capsys) -> None:
    assert main(["data", "inspect", str(PUROMYCIN_CSV)]) == 0

    output = json.loads(capsys.readouterr().out)
    assert output["valid"] is True
    assert output["row_count"] == 12


def test_invalid_kinetics_data_is_reported(tmp_path: Path) -> None:
    path = tmp_path / "invalid.csv"
    path.write_text(
        "substrate_conc,reaction_velocity\n-1,10\n0.1,-2\n0.1,3\n",
        encoding="utf-8",
    )

    report = inspect_csv(path)
    codes = {issue.code for issue in report.issues}
    assert not report.valid
    assert {
        "negative_concentration",
        "negative_velocity",
        "insufficient_concentration_levels",
    } <= codes
