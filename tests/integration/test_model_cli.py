"""CLI integration tests for end-to-end scientific modeling workflow."""

import json
from pathlib import Path

import pytest

from scimodel.interfaces.cli import main

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SYNTHETIC_CSV = PROJECT_ROOT / "examples" / "enzyme_kinetics_synthetic.csv"
PUROMYCIN_CSV = PROJECT_ROOT / "examples" / "enzyme_kinetics_puromycin.csv"


def test_model_fit_cli_outputs_structured_result(capsys: pytest.CaptureFixture[str]) -> None:
    """The CLI 'model fit' command returns structured JSON with parameter estimates."""
    assert main(["model", "fit", str(SYNTHETIC_CSV)]) == 0

    result = json.loads(capsys.readouterr().out)
    assert result["model"] == "michaelis_menten"
    assert result["status"] == "converged"
    assert result["parameters"]["vmax"] > 0
    assert result["parameters"]["km"] > 0


def test_model_validate_cli_outputs_structured_result(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The CLI 'model validate' command validates fit, diagnostics, and assumptions."""
    assert main(["model", "validate", str(PUROMYCIN_CSV)]) == 0

    output = json.loads(capsys.readouterr().out)
    assert "fit" in output
    assert "validation" in output
    assert output["validation"]["valid"] is True
    assert output["validation"]["model"] == "michaelis_menten"
    assert any(
        check["name"] == "goodness_of_fit" and check["passed"]
        for check in output["validation"]["checks"]
    )


def test_report_build_cli_generates_all_artifacts(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The CLI 'report build' command writes Markdown report, JSON manifest, fit, and validation."""
    output_dir = tmp_path / "cli_report"
    assert main(["report", "build", str(PUROMYCIN_CSV), "--output-dir", str(output_dir)]) == 0

    summary = json.loads(capsys.readouterr().out)
    assert summary["valid"] is True

    # Verify all four generated artifacts on disk
    artifacts = summary["artifacts"]
    report_file = Path(artifacts["report"])
    manifest_file = Path(artifacts["manifest"])
    fit_file = Path(artifacts["fit_result"])
    val_file = Path(artifacts["validation"])

    assert report_file.is_file()
    assert manifest_file.is_file()
    assert fit_file.is_file()
    assert val_file.is_file()

    # Verify report contents
    report_text = report_file.read_text(encoding="utf-8")
    assert "# SciModel Validation Report" in report_text
    assert "Vmax" in report_text
    assert "Km" in report_text


def test_end_to_end_simple_task_workflow(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Execute the full end-to-end simple task pipeline: inspect -> fit -> validate -> report."""
    # Step 1: Inspect data
    assert main(["data", "inspect", str(PUROMYCIN_CSV)]) == 0
    inspect_out = json.loads(capsys.readouterr().out)
    assert inspect_out["valid"] is True
    assert inspect_out["row_count"] == 12

    # Step 2: Fit model
    assert main(["model", "fit", str(PUROMYCIN_CSV)]) == 0
    fit_out = json.loads(capsys.readouterr().out)
    assert fit_out["converged"] is True
    assert 210.0 < fit_out["parameters"]["vmax"] < 215.0

    # Step 3: Validate model
    assert main(["model", "validate", str(PUROMYCIN_CSV)]) == 0
    val_out = json.loads(capsys.readouterr().out)
    assert val_out["validation"]["valid"] is True

    # Step 4: Build reproducible report
    report_dir = tmp_path / "e2e_report"
    assert main(["report", "build", str(PUROMYCIN_CSV), "--output-dir", str(report_dir)]) == 0
    build_out = json.loads(capsys.readouterr().out)
    assert build_out["valid"] is True
    assert (report_dir / "report.md").is_file()
    assert (report_dir / "run_manifest.json").is_file()
