"""Failure behavior tests for the model CLI."""

from pathlib import Path

import pytest

from scimodel.interfaces.cli import main


def test_model_fit_cli_rejects_invalid_data(tmp_path: Path) -> None:
    path = tmp_path / "invalid.csv"
    path.write_text(
        "substrate_conc,reaction_velocity\n0.1,10\n0.2,-20\n0.3,30\n0.4,40\n",
        encoding="utf-8",
    )

    with pytest.raises(SystemExit) as raised:
        main(["model", "fit", str(path)])

    assert raised.value.code == 2
