"""Tests for the Phase 1 command-line boundary."""

import pytest

from scimodel import __version__
from scimodel.interfaces.cli import main


def test_cli_help(capsys: pytest.CaptureFixture[str]) -> None:
    """The top-level CLI prints usable help without application modules."""
    assert main([]) == 0
    output = capsys.readouterr().out
    assert "usage: scimodel" in output
    assert "--version" in output


def test_cli_version(capsys: pytest.CaptureFixture[str]) -> None:
    """The CLI exposes the package version."""
    with pytest.raises(SystemExit) as raised:
        main(["--version"])

    assert raised.value.code == 0
    assert capsys.readouterr().out.strip() == f"scimodel {__version__}"
