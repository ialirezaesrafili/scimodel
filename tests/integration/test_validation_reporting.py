"""Integration tests for Phase 4 validation and reporting."""

import json
from pathlib import Path

from scimodel.application.validate_kinetics import validate_csv
from scimodel.reporting.build_report import build_csv_report

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SYNTHETIC_CSV = PROJECT_ROOT / "examples" / "enzyme_kinetics_synthetic.csv"


def test_validation_passes_and_exposes_diagnostics() -> None:
    _, validation = validate_csv(SYNTHETIC_CSV)

    assert validation.valid
    assert all(check.passed for check in validation.checks)
    assert validation.diagnostics["predictions_monotonic"] is True
    assert validation.diagnostics["residual_sign_runs"] >= 1
    assert validation.data_quality["error_count"] == 0
    assert validation.assumptions
    assert validation.limitations


def test_report_build_writes_reproducible_artifacts(tmp_path: Path) -> None:
    artifacts, valid = build_csv_report(SYNTHETIC_CSV, tmp_path / "run")

    assert valid
    assert all(path.is_file() for path in artifacts.__dict__.values())
    manifest = json.loads(artifacts.manifest.read_text(encoding="utf-8"))
    report = artifacts.report.read_text(encoding="utf-8")
    assert len(manifest["input"]["sha256"]) == 64
    assert "Parameter estimates" in report
    assert "Validation checks" in report
    assert "Model assumptions" in report
    assert "95% confidence interval" in report
    assert "run_manifest.json" in report
