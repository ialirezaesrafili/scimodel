"""CLI integration tests for Phase 3 model fitting."""

import json
from pathlib import Path

from scimodel.interfaces.cli import main

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SYNTHETIC_CSV = PROJECT_ROOT / "examples" / "enzyme_kinetics_synthetic.csv"


def test_model_fit_cli_outputs_structured_result(capsys) -> None:
    assert main(["model", "fit", str(SYNTHETIC_CSV)]) == 0

    result = json.loads(capsys.readouterr().out)
    assert result["model"] == "michaelis_menten"
    assert result["status"] == "converged"
    assert result["parameters"]["vmax"] > 0
