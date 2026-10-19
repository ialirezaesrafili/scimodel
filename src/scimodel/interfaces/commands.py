"""General-purpose discovery commands: start, scan, profile, suggest, discover, config, llm."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

from scimodel.adapters.llm import PROVIDERS, create_language_model
from scimodel.adapters.tabular_reader import TableReadError, read_table
from scimodel.application.discovery import ENGINES, DiscoveryOptions, discover
from scimodel.application.profiling import profile_dataset
from scimodel.application.session import ResearchSession
from scimodel.application.suggestions import suggest_actions
from scimodel.application.workspace import scan_workspace
from scimodel.domain.dataset import DatasetError
from scimodel.domain.discovery import EXPERTISE_LEVELS
from scimodel.domain.fit import ModelFitError
from scimodel.domain.ports import LanguageModelError, LanguageModelPort
from scimodel.infrastructure.config import ConfigError, Settings, load_settings, save_setting
from scimodel.interfaces.interactive import StreamTerminal, run_interactive
from scimodel.reporting.discovery_report import write_discovery_report

COMMANDS = frozenset({"start", "scan", "profile", "suggest", "discover", "config", "llm"})


def register(subparsers: Any) -> None:
    start = subparsers.add_parser("start", help="Start the interactive assistant in a folder.")
    start.add_argument("folder", nargs="?", type=Path, default=Path("."))
    _llm_options(start)

    scan = subparsers.add_parser("scan", help="List analyzable data files in a folder.")
    scan.add_argument("folder", nargs="?", type=Path, default=Path("."))
    scan.add_argument("--json", action="store_true", help="Emit JSON.")

    profile = subparsers.add_parser("profile", help="Profile any tabular dataset.")
    profile.add_argument("path", type=Path)
    profile.add_argument("--target")
    profile.add_argument("--predictors", help="Comma-separated predictor columns.")
    profile.add_argument("--json", action="store_true")

    suggest = subparsers.add_parser("suggest", help="Suggest analyses for a dataset.")
    suggest.add_argument("path", type=Path)
    suggest.add_argument("--level", choices=EXPERTISE_LEVELS)
    suggest.add_argument("--json", action="store_true")

    find = subparsers.add_parser(
        "discover", help="Discover, rank, and quality-grade equations for a dataset."
    )
    find.add_argument("path", type=Path)
    find.add_argument("--target", help="Response column (default: inferred).")
    find.add_argument("--predictors", help="Comma-separated predictors (default: inferred).")
    find.add_argument(
        "--formula", action="append", default=[], help="Your own formula to test (repeatable)."
    )
    find.add_argument(
        "--engines",
        default=",".join(ENGINES),
        help=f"Comma-separated engines from: {', '.join(ENGINES)}.",
    )
    find.add_argument("--objective", default="", help="Research objective in your own words.")
    find.add_argument("--seed", type=int)
    find.add_argument("--time-budget", type=float, help="Seconds for symbolic search.")
    find.add_argument("--level", choices=EXPERTISE_LEVELS)
    find.add_argument("--output-dir", type=Path, help="Write the report bundle here.")
    find.add_argument("--no-report", action="store_true", help="Do not write a report bundle.")
    find.add_argument("--explain", action="store_true", help="Add an AI interpretation.")
    find.add_argument("--json", action="store_true", help="Emit the full result as JSON.")
    _llm_options(find)

    config = subparsers.add_parser("config", help="Show or change SciModel settings.")
    config_sub = config.add_subparsers(dest="config_command", required=True)
    config_sub.add_parser("show", help="Show effective settings.")
    config_set = config_sub.add_parser("set", help="Persist one setting.")
    config_set.add_argument("key")
    config_set.add_argument("value")
    config_set.add_argument("--project", action="store_true", help="Save for this folder only.")

    llm = subparsers.add_parser("llm", help="Language-model provider utilities.")
    llm_sub = llm.add_subparsers(dest="llm_command", required=True)
    status = llm_sub.add_parser("status", help="Show and optionally test the configured provider.")
    status.add_argument("--test", action="store_true", help="Send a short test request.")
    _llm_options(status)


def _llm_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--llm", choices=PROVIDERS, help="Language-model provider override.")
    parser.add_argument("--llm-model", help="Model name override.")
    parser.add_argument(
        "--share-sample",
        action="store_true",
        help="Allow sending up to 25 raw data rows to the language model (off by default).",
    )


def handle(arguments: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    try:
        settings = load_settings(Path.cwd())
    except ConfigError as exc:
        parser.error(str(exc))
    try:
        return _HANDLERS[arguments.command](arguments, settings)
    except (TableReadError, DatasetError, ModelFitError, ConfigError, LanguageModelError) as exc:
        parser.error(str(exc))
    return 2  # pragma: no cover - parser.error exits


def _language_model(arguments: argparse.Namespace, settings: Settings) -> LanguageModelPort | None:
    provider = getattr(arguments, "llm", None) or settings.llm_provider
    model = getattr(arguments, "llm_model", None) or settings.llm_model or None
    return create_language_model(provider, model=model, host=settings.ollama_host)


def _start(arguments: argparse.Namespace, settings: Settings) -> int:
    folder = arguments.folder.resolve()
    if not folder.is_dir():
        raise DatasetError(f"Not a folder: {folder}")
    session = ResearchSession(
        root=folder,
        level=_level(settings.level),
        language_model=_language_model(arguments, settings),
        reports_dir=settings.reports_dir,
        seed=settings.seed,
        time_budget=settings.time_budget,
        share_data_sample=arguments.share_sample or settings.share_data_sample,
    )

    def remember(level: str) -> None:
        try:
            save_setting("level", level)
            save_setting("onboarded", "true")
        except OSError:
            pass

    return run_interactive(
        session, StreamTerminal(), save_level=remember, first_run=not settings.onboarded
    )


def _scan(arguments: argparse.Namespace, settings: Settings) -> int:
    del settings
    entries = scan_workspace(arguments.folder)
    if arguments.json:
        print(json.dumps([entry.to_dict() for entry in entries], indent=2))
        return 0
    if not entries:
        print("No supported data files found.")
        return 0
    for entry in entries:
        status = "ready" if entry.analyzable else (entry.error or "needs ≥2 numeric columns")
        print(f"{entry.relative}\t{entry.rows or '-'} rows\t{status}")
        if entry.numeric_columns:
            print(f"    numeric: {', '.join(entry.numeric_columns)}")
    return 0


def _profile(arguments: argparse.Namespace, settings: Settings) -> int:
    del settings
    dataset = read_table(arguments.path)
    predictors = _split(arguments.predictors)
    profile = profile_dataset(
        dataset, target=arguments.target, predictors=tuple(predictors) if predictors else None
    )
    if arguments.json:
        print(json.dumps(_clean(profile.to_dict()), indent=2))
        return 0
    print(f"{dataset.name}: {profile.rows} rows, {len(profile.columns)} columns")
    for column in profile.columns:
        span = (
            f"{column.minimum:.4g} … {column.maximum:.4g}"
            if column.minimum is not None
            else f"{column.distinct} categories"
        )
        unit = f" [{column.unit}]" if column.unit else ""
        print(f"  {column.label}{unit}: {column.kind}, role={column.role}, {span}")
    print(f"Suggested response: {profile.target}; predictors: {', '.join(profile.predictors)}")
    for relationship in profile.relationships:
        print(
            f"  {relationship.predictor}: ρ={relationship.spearman:.3f} "
            f"{', '.join(relationship.hints)}"
        )
    for issue in profile.issues:
        print(
            f"  {issue.severity}: {issue.message}" + (f" [{issue.column}]" if issue.column else "")
        )
    return 0


def _suggest(arguments: argparse.Namespace, settings: Settings) -> int:
    dataset = read_table(arguments.path)
    profile = profile_dataset(dataset)
    suggestions = suggest_actions(
        profile, level=_level(arguments.level or settings.level), path=str(arguments.path)
    )
    if arguments.json:
        print(json.dumps([s.to_dict() for s in suggestions], indent=2))
        return 0
    for index, suggestion in enumerate(suggestions, start=1):
        print(f"{index}. {suggestion.title}\n   {suggestion.rationale}")
        if suggestion.command:
            print(f"   $ {suggestion.command}")
    return 0


def _discover(arguments: argparse.Namespace, settings: Settings) -> int:
    dataset = read_table(arguments.path)
    predictors = _split(arguments.predictors)
    profile = profile_dataset(
        dataset, target=arguments.target, predictors=tuple(predictors) if predictors else None
    )
    target = arguments.target or profile.target
    predictors = predictors or list(profile.predictors)
    if not target or not predictors:
        raise DatasetError("Could not infer a target and predictors; pass --target/--predictors.")
    engines = tuple(_split(arguments.engines))
    model = _language_model(arguments, settings) if "llm" in engines or arguments.explain else None
    options = DiscoveryOptions(
        engines=engines,
        seed=settings.seed if arguments.seed is None else arguments.seed,
        time_budget=arguments.time_budget or settings.time_budget,
        objective=arguments.objective,
        user_formulas=tuple(arguments.formula),
        language_model=model,
        share_data_sample=arguments.share_sample or settings.share_data_sample,
    )
    progress = None if arguments.json else (lambda m: print(f"· {m}", file=sys.stderr))
    result = discover(
        dataset, target=target, predictors=predictors, options=options, progress=progress
    )
    level = _level(arguments.level or settings.level)
    bundle = None
    if not arguments.no_report:
        session = ResearchSession(root=Path.cwd(), level=level, language_model=model)
        narrative = (
            session.assistant.explain_result(result, level, arguments.objective)
            if arguments.explain
            else None
        )
        directory = arguments.output_dir or Path(settings.reports_dir) / f"{dataset.name}-discovery"
        bundle = write_discovery_report(
            result,
            dataset,
            profile,
            directory,
            level=level,
            narrative=narrative,
            narrative_source=f"{model.provider_name}:{model.model_name}" if model else None,
        )
    if arguments.json:
        payload = result.to_dict()
        payload["report"] = bundle.to_dict() if bundle else None
        print(json.dumps(_clean(payload), indent=2))
        return 0
    best = result.best
    assert best is not None
    print(f"\nBest model: {best.name} ({best.origin})")
    print(f"  {result.target} = {best.expression}")
    for name, value in best.fit.parameters.items():
        print(f"    {name} = {value:.6g} ± {best.fit.standard_errors.get(name, math.nan):.2g}")
    print(f"  R² = {best.fit.metrics['r_squared']:.4f}; CV R² = {best.cv_r_squared:.4f}")
    if best.name in result.quality:
        q = result.quality[best.name]
        print(f"  Quality: grade {q.grade} ({q.score:.0f}/100) — {q.verdict}")
    print("\nTop candidates:")
    for candidate in result.candidates[:5]:
        print(
            f"  {candidate.name:32s} ΔAICc={candidate.delta_aicc:7.2f}  "
            f"w={candidate.akaike_weight:.2f}  CV R²={candidate.cv_r_squared:.4f}"
        )
    if bundle:
        print(f"\nReport: {bundle.report}")
    return 0


def _config(arguments: argparse.Namespace, settings: Settings) -> int:
    if arguments.config_command == "show":
        print(json.dumps(settings.to_dict(), indent=2))
        return 0
    path = save_setting(
        arguments.key, arguments.value, scope="project" if arguments.project else "user"
    )
    print(f"Saved {arguments.key} = {arguments.value} to {path}")
    return 0


def _llm(arguments: argparse.Namespace, settings: Settings) -> int:
    model = _language_model(arguments, settings)
    if model is None:
        print("Language model: disabled. Enable with: scimodel config set llm_provider anthropic")
        return 0
    print(f"Provider: {model.provider_name}\nModel: {model.model_name}")
    if arguments.test:
        reply = model.complete("You are a test endpoint.", "Reply with the single word: ready")
        print(f"Test reply: {reply.strip()[:200]}")
    return 0


_HANDLERS = {
    "start": _start,
    "scan": _scan,
    "profile": _profile,
    "suggest": _suggest,
    "discover": _discover,
    "config": _config,
    "llm": _llm,
}


def _split(value: str | None) -> list[str]:
    return [item.strip() for item in (value or "").split(",") if item.strip()]


def _level(value: str) -> Any:
    return value if value in EXPERTISE_LEVELS else "intermediate"


def _clean(value: Any) -> Any:
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, dict):
        return {str(k): _clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_clean(v) for v in value]
    return value
