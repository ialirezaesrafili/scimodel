"""Interactive terminal assistant: run ``scimodel`` inside a folder that contains data."""

from __future__ import annotations

import math
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Protocol, TextIO

from scimodel import __version__
from scimodel.application.session import ResearchSession
from scimodel.domain.dataset import DatasetError
from scimodel.domain.discovery import EXPERTISE_LEVELS, DiscoveryResult, ExpertiseLevel
from scimodel.domain.fit import ModelFitError
from scimodel.domain.ports import LanguageModelError

HELP = """Commands:
  /help              show this help
  /data              list data files in this folder and switch dataset
  /suggest           show suggestions for the open dataset
  /discover          discover the governing equation (asks for target and predictors)
  /fit <formula>     test your own formula, e.g. /fit A*x/(K + x)
  /report            write a report for the latest result
  /level <name>      novice, intermediate, or expert
  /quit              leave
Anything else is treated as your research goal or a question."""


class Terminal(Protocol):
    def say(self, text: str = "") -> None: ...
    def ask(self, prompt: str) -> str: ...


class StreamTerminal:
    """Terminal backed by text streams; colours only when attached to a TTY."""

    def __init__(self, stdin: TextIO | None = None, stdout: TextIO | None = None) -> None:
        self.stdin = stdin or sys.stdin
        self.stdout = stdout or sys.stdout

    def say(self, text: str = "") -> None:
        self.stdout.write(text + "\n")
        self.stdout.flush()

    def ask(self, prompt: str) -> str:
        self.stdout.write(prompt)
        self.stdout.flush()
        line = self.stdin.readline()
        if not line:
            raise EOFError
        return line.strip()


def run_interactive(
    session: ResearchSession,
    terminal: Terminal,
    *,
    save_level: Callable[[str], None] | None = None,
    first_run: bool = False,
) -> int:
    """Drive the conversation loop. Returns a process exit code."""
    terminal.say(f"SciModel {__version__} — scientific modeling assistant")
    terminal.say(f"Workspace: {session.root}")
    llm = (
        f"{session.language_model.provider_name}:{session.language_model.model_name}"
        if session.language_model
        else "off (deterministic engines only; see 'scimodel config set llm_provider ...')"
    )
    terminal.say(f"Language model: {llm}")
    terminal.say("")
    try:
        if first_run:
            _choose_level(session, terminal, save_level)
        if not _choose_dataset(session, terminal):
            return 0
        _show_suggestions(session, terminal)
        while True:
            text = terminal.ask("\nscimodel> ")
            if not text:
                continue
            if text in ("/quit", "/exit", "quit", "exit"):
                terminal.say("Goodbye.")
                return 0
            _dispatch(session, terminal, text, save_level)
    except (EOFError, KeyboardInterrupt):
        terminal.say("\nGoodbye.")
        return 0


def _dispatch(
    session: ResearchSession,
    terminal: Terminal,
    text: str,
    save_level: Callable[[str], None] | None,
) -> None:
    command, _, argument = text.partition(" ")
    try:
        if command == "/help":
            terminal.say(HELP)
        elif command == "/data":
            _choose_dataset(session, terminal)
        elif command == "/suggest":
            _show_suggestions(session, terminal)
        elif command == "/discover":
            _discover(session, terminal)
        elif command == "/fit":
            if not argument.strip():
                terminal.say("Usage: /fit <formula>, e.g. /fit A*exp(-k*time)")
            else:
                _discover(session, terminal, formulas=[argument.strip()])
        elif command == "/report":
            _report(session, terminal)
        elif command == "/level":
            _set_level(session, terminal, argument.strip(), save_level)
        elif command.startswith("/"):
            terminal.say(f"Unknown command {command}. Type /help.")
        elif text.isdigit():
            _run_suggestion(session, terminal, int(text))
        else:
            _goal(session, terminal, text)
    except (DatasetError, ModelFitError, LanguageModelError, ValueError) as exc:
        terminal.say(f"⚠ {exc}")


def _choose_level(
    session: ResearchSession, terminal: Terminal, save_level: Callable[[str], None] | None
) -> None:
    terminal.say("How familiar are you with mathematical modeling?")
    terminal.say("  1) new to it — explain everything in plain language")
    terminal.say("  2) comfortable with regression")
    terminal.say("  3) expert — give me the full statistics")
    answer = terminal.ask("Choose 1-3 [2]: ") or "2"
    mapping = {"1": "novice", "2": "intermediate", "3": "expert"}
    level = mapping.get(answer, answer if answer in EXPERTISE_LEVELS else "intermediate")
    _set_level(session, terminal, level, save_level)


def _set_level(
    session: ResearchSession,
    terminal: Terminal,
    level: str,
    save_level: Callable[[str], None] | None,
) -> None:
    if level not in EXPERTISE_LEVELS:
        terminal.say(f"Level must be one of: {', '.join(EXPERTISE_LEVELS)}.")
        return
    session.level = _as_level(level)
    if save_level:
        save_level(level)
    terminal.say(f"Explanations set to: {level}.")


def _as_level(value: str) -> ExpertiseLevel:
    for level in EXPERTISE_LEVELS:
        if level == value:
            return level
    return "intermediate"


def _choose_dataset(session: ResearchSession, terminal: Terminal) -> bool:
    entries = [entry for entry in session.scan() if entry.analyzable]
    if not entries:
        terminal.say(
            "No analyzable data files were found here. Put a CSV, TSV, TXT, JSON, or XLSX file "
            "with at least two numeric columns in this folder and run scimodel again."
        )
        return False
    terminal.say(f"Found {len(entries)} dataset(s):")
    for index, entry in enumerate(entries, start=1):
        columns = ", ".join(entry.numeric_columns[:6])
        more = " …" if len(entry.numeric_columns) > 6 else ""
        terminal.say(f"  {index}) {entry.relative} — {entry.rows} rows; {columns}{more}")
    choice = 1
    if len(entries) > 1:
        answer = terminal.ask(f"Which one should we analyze? [1-{len(entries)}, default 1]: ")
        choice = int(answer) if answer.isdigit() and 1 <= int(answer) <= len(entries) else 1
    profile = session.open(Path(entries[choice - 1].path))
    terminal.say("")
    terminal.say(f"Opened {entries[choice - 1].relative}.")
    if profile.target:
        terminal.say(
            f"I think the response is '{profile.target}' and the candidate explanatory "
            f"variable(s) are {', '.join(profile.predictors) or 'none'}."
        )
    for issue in profile.issues:
        terminal.say(f"  • {issue.message}" + (f" [{issue.column}]" if issue.column else ""))
    for relationship in profile.relationships:
        if relationship.hints:
            terminal.say(
                f"  • {relationship.predictor} → {relationship.target}: "
                + ", ".join(h.replace("_", " ") for h in relationship.hints)
            )
    return True


def _show_suggestions(session: ResearchSession, terminal: Terminal) -> None:
    terminal.say("\nWhat you can do (type a number, a goal in your own words, or /help):")
    for index, suggestion in enumerate(_actionable(session), start=1):
        terminal.say(f"  {index}) {suggestion.title}")
        if session.level != "expert":
            terminal.say(f"     {suggestion.rationale}")
    insights = [s for s in session.suggestions() if s.kind == "insight"]
    if insights and session.level != "novice":
        terminal.say("Observations:")
        for insight in insights:
            terminal.say(f"  - {insight.rationale}")


def _actionable(session: ResearchSession) -> list:  # type: ignore[type-arg]
    return [s for s in session.suggestions() if s.kind in ("discover", "quality", "fit", "learn")]


def _run_suggestion(session: ResearchSession, terminal: Terminal, number: int) -> None:
    options = _actionable(session)
    if not 1 <= number <= len(options):
        terminal.say("No suggestion with that number.")
        return
    suggestion = options[number - 1]
    if suggestion.kind == "discover":
        params = suggestion.params
        _discover(session, terminal, target=params["target"], predictors=params["predictors"])
    elif suggestion.kind == "quality":
        _quality_summary(session, terminal)
    elif suggestion.kind == "fit":
        formula = terminal.ask("Formula (use column names as variables): ")
        if formula:
            _discover(session, terminal, formulas=[formula])
    else:
        terminal.say("Type any question, for example: what does the quality grade mean?")


def _quality_summary(session: ResearchSession, terminal: Terminal) -> None:
    profile = session.profile
    if profile is None:
        return
    for column in profile.columns:
        flags = []
        if column.missing:
            flags.append(f"{column.missing} missing")
        if column.outliers:
            flags.append(f"{column.outliers} possible outlier(s)")
        detail = f" ({', '.join(flags)})" if flags else ""
        terminal.say(f"  {column.label}: {column.kind}, role {column.role}{detail}")


def _goal(session: ResearchSession, terminal: Terminal, text: str) -> None:
    if text.rstrip().endswith("?") and session.language_model is not None:
        terminal.say(session.ask(text))
        return
    plan = session.interpret(text)
    if plan.get("intent") == "quality":
        _quality_summary(session, terminal)
        return
    if plan.get("intent") == "report":
        _report(session, terminal)
        return
    if plan.get("intent") == "explain" and session.language_model is None:
        terminal.say(
            "I can explain results in depth when a language model is configured. Meanwhile, "
            "every report includes plain-language explanations (try /level novice)."
        )
        return
    formulas = [plan["formula"]] if plan.get("formula") else []
    _discover(
        session,
        terminal,
        target=plan.get("target"),
        predictors=plan.get("predictors") or None,
        formulas=formulas,
    )


def _discover(
    session: ResearchSession,
    terminal: Terminal,
    *,
    target: str | None = None,
    predictors: Sequence[str] | None = None,
    formulas: Sequence[str] = (),
) -> None:
    profile = session.profile
    if profile is None:
        terminal.say("Open a dataset first (/data).")
        return
    target = target or profile.target
    answer = terminal.ask(f"Response variable [{target}]: ")
    target = answer or target
    default_predictors = [p for p in (predictors or profile.predictors) if p != target]
    answer = terminal.ask(
        f"Explanatory variable(s), comma-separated [{','.join(default_predictors)}]: "
    )
    chosen = [p.strip() for p in answer.split(",") if p.strip()] if answer else default_predictors
    if not target or not chosen:
        terminal.say("A response and at least one explanatory variable are needed.")
        return
    terminal.say("Searching for the governing equation…")
    result = session.run_discovery(
        target, chosen, formulas=formulas, progress=lambda m: terminal.say(f"  · {m}")
    )
    _show_result(session, terminal, result)
    if terminal.ask("\nWrite a full report? [Y/n]: ").lower() not in ("n", "no"):
        _report(session, terminal)


def _show_result(session: ResearchSession, terminal: Terminal, result: DiscoveryResult) -> None:
    best = result.best
    if best is None:
        terminal.say("No model could be fitted.")
        return
    terminal.say("")
    terminal.say(f"Best model: {best.name}  ({best.origin})")
    terminal.say(f"  {result.target} = {best.expression}")
    for name, value in best.fit.parameters.items():
        error = best.fit.standard_errors.get(name, math.nan)
        terminal.say(f"    {name} = {value:.6g} ± {error:.2g}")
    terminal.say(
        f"  R² = {best.fit.metrics['r_squared']:.4f}, cross-validated R² = {best.cv_r_squared:.4f}"
    )
    assessment = result.quality.get(best.name)
    if assessment:
        terminal.say(
            f"  Quality grade {assessment.grade} ({assessment.score:.0f}/100): {assessment.verdict}"
        )
        if session.level == "novice":
            for check in assessment.checks:
                if check.status in ("warn", "fail"):
                    terminal.say(f"    – {check.explanation}")
    rows = result.candidates[: 3 if session.level == "novice" else 6]
    terminal.say("\n  Rank  Model                          ΔAICc   weight  CV R²")
    for rank, candidate in enumerate(rows, start=1):
        terminal.say(
            f"  {rank:>4}  {candidate.name[:30]:30s} {candidate.delta_aicc:7.2f}  "
            f"{candidate.akaike_weight:6.2f}  {candidate.cv_r_squared:.4f}"
        )
    for warning in result.warnings:
        terminal.say(f"  ⚠ {warning}")


def _report(session: ResearchSession, terminal: Terminal) -> None:
    if session.result is None:
        terminal.say("Run a discovery first (/discover).")
        return
    terminal.say("Writing report…")
    bundle = session.write_report()
    terminal.say(f"Report written to {bundle.report}")
    if bundle.figures:
        terminal.say(f"Figures: {', '.join(bundle.figures.values())}")
