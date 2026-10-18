"""Automated private-pilot regression checks for approved datasets."""

import json
from pathlib import Path

import pytest

from scimodel.reporting.build_report import build_csv_report

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATASETS = (
    PROJECT_ROOT / "examples" / "enzyme_kinetics_puromycin.csv",
    PROJECT_ROOT / "examples" / "enzyme_kinetics_synthetic.csv",
)


@pytest.mark.parametrize("dataset", DATASETS, ids=lambda path: path.stem)
def test_approved_dataset_pilot_bundle(dataset: Path, tmp_path: Path) -> None:
    artifacts, valid = build_csv_report(dataset, tmp_path / dataset.stem)

    assert valid
    assert all(path.is_file() for path in artifacts.__dict__.values())
    validation = json.loads(artifacts.validation.read_text(encoding="utf-8"))
    manifest = json.loads(artifacts.manifest.read_text(encoding="utf-8"))
    assert validation["valid"] is True
    assert validation["data_quality"]["error_count"] == 0
    assert len(manifest["input"]["sha256"]) == 64
