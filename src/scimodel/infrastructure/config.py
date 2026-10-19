"""User and project configuration (TOML), with environment-variable overrides.

Precedence (highest first): ``SCIMODEL_*`` environment variables, the project
file ``.scimodel/config.toml`` in the working folder, the user file
``$XDG_CONFIG_HOME/scimodel/config.toml``, then built-in defaults. API keys
are never stored here; providers read their own credentials.
"""

from __future__ import annotations

import os
import tomllib
from dataclasses import asdict, dataclass, fields, replace
from pathlib import Path
from typing import Any

from scimodel.domain.discovery import EXPERTISE_LEVELS

_PROVIDERS = ("none", "anthropic", "ollama")


@dataclass(frozen=True)
class Settings:
    level: str = "intermediate"
    llm_provider: str = "none"
    llm_model: str = ""
    ollama_host: str = "http://localhost:11434"
    share_data_sample: bool = False
    reports_dir: str = "scimodel_reports"
    time_budget: float = 15.0
    seed: int = 0
    onboarded: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ConfigError(ValueError):
    """Raised for unknown keys or invalid values."""


def user_config_path() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / "scimodel" / "config.toml"


def project_config_path(root: Path) -> Path:
    return root / ".scimodel" / "config.toml"


def load_settings(project_root: Path | None = None) -> Settings:
    settings = Settings()
    for path in (user_config_path(), project_config_path(project_root or Path.cwd())):
        if path.is_file():
            settings = _merge(settings, _read(path), str(path))
    environment = {
        field.name: os.environ[f"SCIMODEL_{field.name.upper()}"]
        for field in fields(Settings)
        if f"SCIMODEL_{field.name.upper()}" in os.environ
    }
    return _merge(settings, environment, "environment")


def save_setting(
    key: str, value: str, *, scope: str = "user", project_root: Path | None = None
) -> Path:
    """Validate and persist one setting to the user or project file."""
    validated = _merge(Settings(), {key: value}, "command line")
    path = (
        user_config_path() if scope == "user" else project_config_path(project_root or Path.cwd())
    )
    existing = _read(path) if path.is_file() else {}
    existing[key] = getattr(validated, key)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_dump(existing), encoding="utf-8")
    return path


def _read(path: Path) -> dict[str, Any]:
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"Invalid TOML in {path}: {exc}") from exc


def _merge(settings: Settings, values: dict[str, Any], origin: str) -> Settings:
    known = {field.name: field for field in fields(Settings)}
    updates: dict[str, Any] = {}
    for key, raw in values.items():
        if key not in known:
            raise ConfigError(f"Unknown setting '{key}' in {origin}. Known: {', '.join(known)}.")
        default = getattr(Settings(), key)
        try:
            if isinstance(default, bool):
                value: Any = (
                    raw if isinstance(raw, bool) else str(raw).lower() in ("1", "true", "yes", "on")
                )
            elif isinstance(default, int):
                value = int(raw)
            elif isinstance(default, float):
                value = float(raw)
            else:
                value = str(raw)
        except ValueError as exc:
            raise ConfigError(f"Invalid value for '{key}': {raw!r}") from exc
        updates[key] = value
    merged = replace(settings, **updates)
    if merged.level not in EXPERTISE_LEVELS:
        raise ConfigError(f"level must be one of {', '.join(EXPERTISE_LEVELS)}.")
    if merged.llm_provider not in _PROVIDERS:
        raise ConfigError(f"llm_provider must be one of {', '.join(_PROVIDERS)}.")
    if merged.time_budget <= 0:
        raise ConfigError("time_budget must be positive.")
    return merged


def _dump(values: dict[str, Any]) -> str:
    lines = ["# SciModel configuration — see docs/cli-reference.md", ""]
    for key in sorted(values):
        value = values[key]
        if isinstance(value, bool):
            rendered = "true" if value else "false"
        elif isinstance(value, (int, float)):
            rendered = repr(value)
        else:
            rendered = '"' + str(value).replace("\\", "\\\\").replace('"', '\\"') + '"'
        lines.append(f"{key} = {rendered}")
    return "\n".join(lines) + "\n"
