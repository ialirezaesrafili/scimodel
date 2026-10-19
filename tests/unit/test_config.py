"""Tests for layered TOML configuration."""

from pathlib import Path

import pytest

from scimodel.infrastructure.config import ConfigError, load_settings, save_setting


@pytest.fixture(autouse=True)
def isolated(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "cfg"))
    for name in ("SCIMODEL_LEVEL", "SCIMODEL_LLM_PROVIDER", "SCIMODEL_TIME_BUDGET"):
        monkeypatch.delenv(name, raising=False)


def test_defaults_user_project_and_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    assert load_settings(project).level == "intermediate"
    save_setting("level", "novice")
    save_setting("share_data_sample", "yes")
    save_setting("llm_model", 'quote"d')
    save_setting("time_budget", "30", scope="project", project_root=project)
    settings = load_settings(project)
    assert settings.level == "novice" and settings.share_data_sample is True
    assert settings.llm_model == 'quote"d' and settings.time_budget == 30.0
    monkeypatch.setenv("SCIMODEL_LEVEL", "expert")
    assert load_settings(project).level == "expert"
    assert load_settings(project).to_dict()["time_budget"] == 30.0


@pytest.mark.parametrize(
    ("key", "value", "message"),
    [
        ("level", "guru", "level"),
        ("llm_provider", "x", "llm_provider"),
        ("time_budget", "-1", "positive"),
        ("seed", "abc", "Invalid"),
        ("colour", "1", "Unknown"),
    ],
)
def test_invalid_settings(key: str, value: str, message: str) -> None:
    with pytest.raises(ConfigError, match=message):
        save_setting(key, value)


def test_corrupt_file(tmp_path: Path) -> None:
    path = tmp_path / "cfg" / "scimodel" / "config.toml"
    path.parent.mkdir(parents=True)
    path.write_text("level = = 1")
    with pytest.raises(ConfigError, match="Invalid TOML"):
        load_settings(tmp_path)
