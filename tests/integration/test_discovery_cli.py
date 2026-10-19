"""End-to-end tests for the general-purpose CLI and the interactive assistant."""

import io
import json
import shutil
from pathlib import Path

import pytest

from scimodel.application.session import ResearchSession
from scimodel.domain.dataset import DatasetError
from scimodel.interfaces.cli import main
from scimodel.interfaces.interactive import StreamTerminal, run_interactive

EXAMPLES = Path(__file__).resolve().parents[2] / "examples"


@pytest.fixture(autouse=True)
def isolated_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("SCIMODEL_TIME_BUDGET", "3")
    monkeypatch.chdir(tmp_path)


def test_scan_profile_suggest(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["scan", str(EXAMPLES)]) == 0
    assert "kepler_planets.csv" in capsys.readouterr().out
    assert main(["scan", str(EXAMPLES), "--json"]) == 0
    assert any(e["analyzable"] for e in json.loads(capsys.readouterr().out))
    assert main(["profile", str(EXAMPLES / "catalysis_arrhenius.csv")]) == 0
    assert "Suggested response: rate" in capsys.readouterr().out
    assert (
        main(
            [
                "profile",
                str(EXAMPLES / "kepler_planets.csv"),
                "--json",
                "--target",
                "orbital_period",
                "--predictors",
                "semi_major_axis",
            ]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out)["predictors"] == ["semi_major_axis"]
    assert main(["suggest", str(EXAMPLES / "kepler_planets.csv"), "--level", "novice"]) == 0
    assert "Discover the equation" in capsys.readouterr().out
    assert main(["suggest", str(EXAMPLES / "kepler_planets.csv"), "--json"]) == 0
    assert json.loads(capsys.readouterr().out)[0]["title"]


def test_discover_json_with_report_bundle(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = tmp_path / "report"
    code = main(
        [
            "discover",
            str(EXAMPLES / "kepler_planets.csv"),
            "--target",
            "orbital_period",
            "--predictors",
            "semi_major_axis",
            "--engines",
            "library,sparse",
            "--formula",
            "c*semi_major_axis**1.5",
            "--formula",
            "bad((",
            "--output-dir",
            str(out),
            "--json",
            "--level",
            "novice",
        ]
    )
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["best"] in ("user_1", "power_law")
    assert any(c["origin"] == "user" for c in payload["candidates"])
    assert any(r["expression"] == "bad((" for r in payload["rejected"])
    report = (out / "report.md").read_text()
    assert "## Glossary" in report and "Recommended model" in report
    assert json.loads((out / "run_manifest.json").read_text())["input"]["sha256"]
    assert (out / "figures" / "fit.png").is_file()


def test_discover_text_output_and_errors(capsys: pytest.CaptureFixture[str]) -> None:
    assert (
        main(
            [
                "discover",
                str(EXAMPLES / "enzyme_kinetics_synthetic.csv"),
                "--engines",
                "library",
                "--no-report",
                "--level",
                "expert",
            ]
        )
        == 0
    )
    output = capsys.readouterr().out
    assert "Best model: saturation_hyperbolic" in output and "Report:" not in output
    with pytest.raises(SystemExit) as raised:
        main(["discover", str(EXAMPLES / "missing.csv")])
    assert raised.value.code == 2
    with pytest.raises(SystemExit):
        main(["discover", str(EXAMPLES / "kepler_planets.csv"), "--target", "planet"])


def test_config_and_llm_status(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["config", "set", "level", "expert"]) == 0
    assert main(["config", "show"]) == 0
    assert '"level": "expert"' in capsys.readouterr().out
    assert main(["config", "set", "time_budget", "5", "--project"]) == 0
    assert main(["llm", "status"]) == 0
    assert "disabled" in capsys.readouterr().out
    assert main(["llm", "status", "--llm", "ollama", "--llm-model", "m"]) == 0
    assert "Model: m" in capsys.readouterr().out
    with pytest.raises(SystemExit):
        main(["config", "set", "level", "wizard"])


def _script(
    tmp_path: Path, answers: list[str]
) -> tuple[ResearchSession, StreamTerminal, io.StringIO]:
    shutil.copy(EXAMPLES / "enzyme_kinetics_puromycin.csv", tmp_path / "assay.csv")
    shutil.copy(EXAMPLES / "kepler_planets.csv", tmp_path / "planets.csv")
    output = io.StringIO()
    terminal = StreamTerminal(io.StringIO("\n".join(answers) + "\n"), output)
    session = ResearchSession(root=tmp_path, time_budget=2)
    return session, terminal, output


def test_interactive_novice_session_end_to_end(tmp_path: Path) -> None:
    saved: list[str] = []
    session, terminal, output = _script(
        tmp_path,
        [
            "1",  # level: novice
            "1",  # dataset: assay.csv
            "/help",
            "/level wizard",
            "/suggest",
            "/bogus",
            "1",  # suggestion 1: discover
            "",
            "",  # accept target and predictors
            "y",  # write report
            "how does reaction_velocity depend on substrate_conc",
            "",
            "",
            "n",
            "/fit Vmax*substrate_conc/(K + substrate_conc)",
            "",
            "",
            "n",
            "/fit",
            "check for outliers",
            "99",
            "/report",
            "/quit",
        ],
    )
    assert run_interactive(session, terminal, save_level=saved.append, first_run=True) == 0
    text = output.getvalue()
    assert saved == ["novice"]
    assert "Found 2 dataset(s)" in text and "Opened assay.csv" in text
    assert "Best model: saturation_hyperbolic" in text and "Quality grade" in text
    assert "Report written to" in text and "Unknown command" in text
    assert "No suggestion with that number" in text and "Goodbye" in text
    assert list((tmp_path / "scimodel_reports").glob("*/report.md"))


def test_interactive_without_data_and_eof(tmp_path: Path) -> None:
    output = io.StringIO()
    empty = ResearchSession(root=tmp_path)
    assert run_interactive(empty, StreamTerminal(io.StringIO(""), output)) == 0
    assert "No analyzable data files" in output.getvalue()
    session, terminal, output = _script(tmp_path, ["2", "/data", "1"])
    assert run_interactive(session, terminal) == 0  # input ends -> graceful goodbye
    assert output.getvalue().count("Opened") == 2


def test_session_guards(tmp_path: Path) -> None:
    session = ResearchSession(root=tmp_path)
    with pytest.raises(DatasetError):
        session.suggestions()
    with pytest.raises(DatasetError):
        session.write_report()
    session.open(EXAMPLES / "kepler_planets.csv")
    with pytest.raises(DatasetError, match="Run a discovery"):
        session.write_report()
    assert session.history[0]["action"] == "open"


def test_start_command_rejects_missing_folder() -> None:
    with pytest.raises(SystemExit):
        main(["start", "/definitely/not/here"])
