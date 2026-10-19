"""Tests for dataset profiling, suggestions, and workspace scanning."""

from pathlib import Path

import numpy as np

from scimodel.adapters.tabular_reader import build_dataset, read_table
from scimodel.application.profiling import dominant_frequency, profile_dataset
from scimodel.application.suggestions import suggest_actions
from scimodel.application.workspace import scan_workspace

EXAMPLES = Path(__file__).resolve().parents[2] / "examples"


def _dataset(columns: dict[str, list[float]]):  # type: ignore[no-untyped-def]
    names = list(columns)
    rows = [[str(columns[n][i]) for n in names] for i in range(len(columns[names[0]]))]
    return build_dataset("synthetic", "<memory>", names, rows)


def test_roles_target_and_issues_on_real_lab_file() -> None:
    profile = profile_dataset(read_table(EXAMPLES / "catalysis_arrhenius.csv"))
    roles = {c.name: c.role for c in profile.columns}
    assert roles["run_id"] == "label" and roles["replicate"] == "index"
    assert roles["temperature"] == "temperature" and roles["operator"] == "grouping"
    assert profile.target == "rate"
    assert profile.predictors == ("temperature", "catalyst_loading")
    codes = {issue.code for issue in profile.issues}
    assert {"missing_values", "possible_outliers"} <= codes
    assert profile.replicated_predictor_levels > 0


def test_target_tokens_do_not_match_substrings() -> None:
    profile = profile_dataset(read_table(EXAMPLES / "enzyme_kinetics_puromycin.csv"))
    assert profile.target == "reaction_velocity"
    assert "saturating" in profile.relationships[0].hints


def test_time_column_is_not_an_index() -> None:
    profile = profile_dataset(read_table(EXAMPLES / "non_kinetics_exponential_decay.csv"))
    assert profile.column("time").role == "time"  # type: ignore[union-attr]
    assert profile.predictors == ("time",)
    assert "exponential_like" in profile.relationships[0].hints


def test_shape_hints() -> None:
    x = np.linspace(0.1, 10, 40)
    sigmoid = profile_dataset(
        _dataset({"x": list(x), "signal": list(1 / (1 + np.exp(-2 * (x - 5))))})
    )
    assert "sigmoidal" in sigmoid.relationships[0].hints
    power = profile_dataset(_dataset({"x": list(x), "response": list(3 * x**1.7)}))
    assert "power_law_like" in power.relationships[0].hints
    wave = profile_dataset(_dataset({"x": list(x), "response": list(np.sin(3 * x))}))
    assert "oscillating" in wave.relationships[0].hints
    assert abs(dominant_frequency(x, np.sin(3 * x)) - 3) < 0.5
    peak = profile_dataset(_dataset({"x": list(x), "response": list(np.exp(-((x - 5) ** 2)))}))
    assert "peak" in peak.relationships[0].hints
    flat = profile_dataset(
        _dataset({"x": list(x), "response": list(np.random.default_rng(0).normal(size=40))})
    )
    assert "weak_relationship" in flat.relationships[0].hints


def test_small_sample_and_constant_columns() -> None:
    profile = profile_dataset(_dataset({"x": [1, 2, 3], "c": [5, 5, 5], "y": [1, 4, 9]}))
    codes = {issue.code for issue in profile.issues}
    assert {"small_sample", "constant_column"} <= codes
    assert profile.relationships[0].hints == ("insufficient_variation",)


def test_suggestions_cover_levels_and_multiple_predictors() -> None:
    profile = profile_dataset(read_table(EXAMPLES / "catalysis_arrhenius.csv"))
    kinds = [s.kind for s in suggest_actions(profile, level="novice")]
    assert kinds[0] in ("quality", "discover") and "learn" in kinds
    titles = [s.title for s in suggest_actions(profile)]
    assert any("Isolate the effect of temperature" in t for t in titles)
    discover = next(s for s in suggest_actions(profile) if s.kind == "discover")
    assert discover.params == {"target": "rate", "predictors": ["temperature", "catalyst_loading"]}
    assert "scimodel discover" in discover.command
    lonely = profile_dataset(_dataset({"y": [1, 2, 3, 4, 5]}))
    assert suggest_actions(lonely)[0].kind == "data"


def test_workspace_scan(tmp_path: Path) -> None:
    (tmp_path / "good.csv").write_text("x,y\n1,2\n2,4\n3,7\n")
    (tmp_path / "one_column.csv").write_text("x\n1\n2\n")
    (tmp_path / "broken.csv").write_text("x,x\n1,2\n")
    (tmp_path / "notes.md").write_text("ignored")
    hidden = tmp_path / ".venv"
    hidden.mkdir()
    (hidden / "skip.csv").write_text("x,y\n1,2\n")
    entries = scan_workspace(tmp_path)
    assert [e.relative for e in entries] == ["good.csv", "broken.csv", "one_column.csv"]
    assert entries[0].analyzable and entries[0].to_dict()["analyzable"]
    assert entries[1].error and not entries[2].analyzable
    assert scan_workspace(tmp_path / "good.csv")[0].rows == 3
    assert len(scan_workspace(tmp_path, max_files=1)) == 1
