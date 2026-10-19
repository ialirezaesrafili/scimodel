"""Command-line entry point for SciModel."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Sequence
from dataclasses import asdict
from pathlib import Path
from typing import Any

import numpy as np

from scimodel import __version__
from scimodel.adapters.csv_reader import CsvReadError, read_csv
from scimodel.adapters.matlab_solver import MatlabFormulaSolver, MatlabUnavailableError
from scimodel.adapters.scipy_formula_solver import ScipyFormulaSolver
from scimodel.application.assistant_workflow import (
    run_assistant,
    save_run,
)
from scimodel.application.compare_models import compare_csv_models
from scimodel.application.fit_kinetics import fit_csv
from scimodel.application.inspect_data import inspect_csv
from scimodel.application.providers import JsonPlanProvider, ProviderPlanError
from scimodel.application.recommender import RuleBasedFormulaRecommender
from scimodel.application.validate_kinetics import validate_csv
from scimodel.domain.assistant import TaskRequest
from scimodel.domain.fit import ModelFitError
from scimodel.domain.formula import RESERVED_NAMES, ModelFormula, ParameterSpec
from scimodel.evaluation.runner import compare_evaluations, evaluate_suite, save_evaluation
from scimodel.infrastructure.context_store import ContextStore
from scimodel.infrastructure.recommendation_store import RecommendationStore
from scimodel.infrastructure.run_store import RunStore, compare_runs
from scimodel.interfaces import commands
from scimodel.reporting.build_report import build_csv_report


def parse_parameter_specs(
    expression: str, independent_var: str, params_arg: str | None
) -> list[ParameterSpec]:
    """Parse parameter specifications or infer parameter names from expression."""
    if params_arg:
        specs: list[ParameterSpec] = []
        for item in params_arg.split(","):
            parts = item.strip().split(":")
            name = parts[0].strip()
            lb = float(parts[1]) if len(parts) > 1 else 0.0
            ub = float(parts[2]) if len(parts) > 2 else float("inf")
            specs.append(ParameterSpec(name, lower_bound=lb, upper_bound=ub))
        return specs

    tokens = set(re.findall(r"\b[a-zA-Z_][a-zA-Z0-9_]*\b", expression))
    reserved = set(RESERVED_NAMES) | {independent_var}
    param_names = sorted(tokens - reserved)
    return [ParameterSpec(name, lower_bound=0.0, upper_bound=float("inf")) for name in param_names]


def build_parser() -> argparse.ArgumentParser:
    """Build the top-level SciModel argument parser."""
    parser = argparse.ArgumentParser(
        prog="scimodel",
        description=(
            "A transparent and reproducible scientific modeling assistant. Run 'scimodel' "
            "(or 'scimodel start') inside a folder with data for the interactive assistant."
        ),
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
        help="Show the installed SciModel version and exit.",
    )
    subparsers = parser.add_subparsers(dest="command")
    commands.register(subparsers)

    # data inspect
    data_parser = subparsers.add_parser("data", help="Inspect scientific data inputs.")
    data_subparsers = data_parser.add_subparsers(dest="data_command", required=True)
    inspect_parser = data_subparsers.add_parser(
        "inspect", help="Profile and validate a CSV dataset."
    )
    inspect_parser.add_argument("path", type=Path, help="Path to the CSV dataset.")
    inspect_parser.add_argument(
        "--x-column", default="substrate_conc", help="Substrate concentration column."
    )
    inspect_parser.add_argument(
        "--y-column", default="reaction_velocity", help="Reaction velocity column."
    )

    # model fit / validate
    model_parser = subparsers.add_parser("model", help="Fit scientific models.")
    model_subparsers = model_parser.add_subparsers(dest="model_command", required=True)
    fit_parser = model_subparsers.add_parser(
        "fit", help="Fit the bounded Michaelis–Menten model to a CSV dataset."
    )
    fit_parser.add_argument("path", type=Path, help="Path to the CSV dataset.")
    fit_parser.add_argument(
        "--x-column", default="substrate_conc", help="Substrate concentration column."
    )
    fit_parser.add_argument(
        "--y-column", default="reaction_velocity", help="Reaction velocity column."
    )

    validate_parser = model_subparsers.add_parser(
        "validate", help="Validate a fitted Michaelis–Menten model."
    )
    validate_parser.add_argument("path", type=Path, help="Path to the CSV dataset.")
    validate_parser.add_argument("--x-column", default="substrate_conc")
    validate_parser.add_argument("--y-column", default="reaction_velocity")

    # formula recommend / fit
    formula_parser = subparsers.add_parser(
        "formula", help="Extensible formula modeling and recommendations."
    )
    formula_subparsers = formula_parser.add_subparsers(dest="formula_command", required=True)

    recommend_parser = formula_subparsers.add_parser(
        "recommend", help="Recommend candidate formulas for dataset."
    )
    recommend_parser.add_argument("path", type=Path, help="Path to the CSV dataset.")
    recommend_parser.add_argument(
        "--objective", default="enzyme kinetics", help="Research objective."
    )
    recommend_parser.add_argument("--x-column", default="substrate_conc")
    recommend_parser.add_argument("--y-column", default="reaction_velocity")

    formula_fit_parser = formula_subparsers.add_parser(
        "fit", help="Fit any arbitrary formula using SciPy or MATLAB."
    )
    formula_fit_parser.add_argument("path", type=Path, help="Path to the CSV dataset.")
    formula_fit_parser.add_argument(
        "--formula", required=True, help="Mathematical expression (e.g. '(Vmax*s)/(Km+s)')."
    )
    formula_fit_parser.add_argument(
        "--params", default=None, help="Parameter specs (e.g. 'Vmax:0:inf,Km:0:inf')."
    )
    formula_fit_parser.add_argument(
        "--backend", choices=["scipy", "matlab"], default="scipy", help="Solver backend."
    )
    formula_fit_parser.add_argument(
        "--fallback-to-scipy", action="store_true", help="Fallback if MATLAB unavailable."
    )
    formula_fit_parser.add_argument("--x-column", default="substrate_conc")
    formula_fit_parser.add_argument("--y-column", default="reaction_velocity")
    formula_compare_parser = formula_subparsers.add_parser(
        "compare", help="Compare recommended formulas without selecting one."
    )
    formula_compare_parser.add_argument("path", type=Path)
    formula_compare_parser.add_argument("--objective", default="enzyme kinetics")
    formula_compare_parser.add_argument("--x-column", default="substrate_conc")
    formula_compare_parser.add_argument("--y-column", default="reaction_velocity")

    # report build
    report_parser = subparsers.add_parser("report", help="Build reproducible reports.")
    report_subparsers = report_parser.add_subparsers(dest="report_command", required=True)
    build_parser = report_subparsers.add_parser("build", help="Build a validation report bundle.")
    build_parser.add_argument("path", type=Path, help="Path to the CSV dataset.")
    build_parser.add_argument("--output-dir", type=Path, required=True)
    build_parser.add_argument("--x-column", default="substrate_conc")
    build_parser.add_argument("--y-column", default="reaction_velocity")

    assistant_parser = subparsers.add_parser(
        "assistant", help="Run the transparent assistant workflow."
    )
    assistant_subparsers = assistant_parser.add_subparsers(dest="assistant_command", required=True)
    run_parser = assistant_subparsers.add_parser(
        "run", help="Plan, execute, verify, and report one supported scientific task."
    )
    run_parser.add_argument("path", type=Path, help="Path to the CSV dataset.")
    run_parser.add_argument("--goal", required=True, help="The scientific task objective.")
    run_parser.add_argument("--mode", choices=["normal", "verbose", "audit"], default="normal")
    run_parser.add_argument("--output-dir", type=Path, default=Path("reports/assistant-run"))
    run_parser.add_argument("--x-column", default="substrate_conc")
    run_parser.add_argument("--y-column", default="reaction_velocity")
    run_parser.add_argument("--history-dir", type=Path, default=Path(".scimodel/runs"))
    run_parser.add_argument("--context-dir", type=Path, default=Path(".scimodel/context"))
    run_parser.add_argument(
        "--recommendation-dir", type=Path, default=Path(".scimodel/recommendations")
    )
    run_parser.add_argument(
        "--provider-plan",
        type=Path,
        help="Use a validated provider-generated JSON plan instead of the deterministic planner.",
    )
    history_parser = assistant_subparsers.add_parser("history", help="List stored assistant runs.")
    history_parser.add_argument("--history-dir", type=Path, default=Path(".scimodel/runs"))
    show_parser = assistant_subparsers.add_parser("show", help="Show one stored assistant run.")
    show_parser.add_argument("run_id")
    show_parser.add_argument("--history-dir", type=Path, default=Path(".scimodel/runs"))
    compare_parser = assistant_subparsers.add_parser("compare", help="Compare two stored runs.")
    compare_parser.add_argument("first_run")
    compare_parser.add_argument("second_run")
    compare_parser.add_argument("--history-dir", type=Path, default=Path(".scimodel/runs"))
    context_parser = assistant_subparsers.add_parser(
        "context", help="Manage stored assistant context."
    )
    context_subparsers = context_parser.add_subparsers(dest="context_command", required=True)
    context_set = context_subparsers.add_parser("set", help="Create or update a context item.")
    context_set.add_argument("key")
    context_set.add_argument("value")
    context_set.add_argument("--kind", choices=["preference", "fact", "constraint"], default="fact")
    context_set.add_argument("--source", default="user")
    context_set.add_argument("--confidence", choices=["low", "medium", "high"], default="high")
    context_set.add_argument(
        "--status", choices=["active", "uncertain", "rejected"], default="active"
    )
    context_set.add_argument("--context-dir", type=Path, default=Path(".scimodel/context"))
    context_list = context_subparsers.add_parser("list", help="List stored context items.")
    context_list.add_argument("--context-dir", type=Path, default=Path(".scimodel/context"))
    context_show = context_subparsers.add_parser("show", help="Show one context item.")
    context_show.add_argument("key")
    context_show.add_argument("--context-dir", type=Path, default=Path(".scimodel/context"))
    context_remove = context_subparsers.add_parser("remove", help="Remove one context item.")
    context_remove.add_argument("key")
    context_remove.add_argument("--context-dir", type=Path, default=Path(".scimodel/context"))
    recommendation_parser = assistant_subparsers.add_parser(
        "recommendation", help="Review assistant recommendations."
    )
    recommendation_subparsers = recommendation_parser.add_subparsers(
        dest="recommendation_command", required=True
    )
    recommendation_list = recommendation_subparsers.add_parser("list", help="List recommendations.")
    recommendation_list.add_argument(
        "--recommendation-dir", type=Path, default=Path(".scimodel/recommendations")
    )
    recommendation_show = recommendation_subparsers.add_parser(
        "show", help="Show one recommendation."
    )
    recommendation_show.add_argument("recommendation_id")
    recommendation_show.add_argument(
        "--recommendation-dir", type=Path, default=Path(".scimodel/recommendations")
    )
    for command in ("accept", "reject"):
        recommendation_action = recommendation_subparsers.add_parser(command)
        recommendation_action.add_argument("recommendation_id")
        recommendation_action.add_argument("--reason", default="")
        recommendation_action.add_argument(
            "--recommendation-dir", type=Path, default=Path(".scimodel/recommendations")
        )
    recommendation_correct = recommendation_subparsers.add_parser(
        "correct", help="Correct a recommendation and record why."
    )
    recommendation_correct.add_argument("recommendation_id")
    recommendation_correct.add_argument("--action", required=True)
    recommendation_correct.add_argument("--reason", required=True)
    recommendation_correct.add_argument(
        "--recommendation-dir", type=Path, default=Path(".scimodel/recommendations")
    )
    evaluate_parser = assistant_subparsers.add_parser(
        "evaluate", help="Run or compare the assistant benchmark suite."
    )
    evaluate_parser.add_argument("--project-root", type=Path, default=Path.cwd())
    evaluate_parser.add_argument("--output-dir", type=Path, default=Path("reports/evaluation"))
    evaluate_parser.add_argument("--compare", nargs=2, metavar=("FIRST", "SECOND"))

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the SciModel CLI and return a process exit code."""
    parser = build_parser()
    if argv is None and len(sys.argv) == 1 and sys.stdin.isatty() and sys.stdout.isatty():
        argv = ["start"]
    arguments = parser.parse_args(argv)

    if arguments.command in commands.COMMANDS:
        return commands.handle(arguments, parser)

    if arguments.command == "data" and arguments.data_command == "inspect":
        try:
            report = inspect_csv(
                arguments.path, x_column=arguments.x_column, y_column=arguments.y_column
            )
        except CsvReadError as exc:
            parser.error(str(exc))
        print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
        return 0 if report.valid else 2

    if arguments.command == "model" and arguments.model_command == "fit":
        try:
            result = fit_csv(
                arguments.path, x_column=arguments.x_column, y_column=arguments.y_column
            )
        except (CsvReadError, ModelFitError) as exc:
            parser.error(str(exc))
        print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
        return 0 if result.converged else 2

    if arguments.command == "model" and arguments.model_command == "validate":
        try:
            result, validation = validate_csv(
                arguments.path, x_column=arguments.x_column, y_column=arguments.y_column
            )
        except (CsvReadError, ModelFitError) as exc:
            parser.error(str(exc))
        output = {"fit": result.to_dict(), "validation": validation.to_dict()}
        print(json.dumps(output, indent=2, sort_keys=True))
        return 0 if validation.valid else 2

    if arguments.command == "formula" and arguments.formula_command == "recommend":
        try:
            inspection_rep = inspect_csv(
                arguments.path, x_column=arguments.x_column, y_column=arguments.y_column
            )
        except CsvReadError as exc:
            parser.error(str(exc))
        recommender = RuleBasedFormulaRecommender()
        recs = recommender.recommend(inspection_rep, objective=arguments.objective)
        rec_output = [
            {
                "formula_name": rec.formula.name,
                "expression": rec.formula.expression,
                "parameters": [p.name for p in rec.formula.parameters],
                "confidence_score": rec.confidence_score,
                "scientific_rationale": rec.scientific_rationale,
                "assumptions": list(rec.formula.assumptions),
            }
            for rec in recs
        ]
        print(json.dumps(rec_output, indent=2))
        return 0

    if arguments.command == "formula" and arguments.formula_command == "fit":
        try:
            table = read_csv(arguments.path)
            x_vals = np.array([float(row[arguments.x_column]) for row in table.rows], dtype=float)
            y_vals = np.array([float(row[arguments.y_column]) for row in table.rows], dtype=float)
            params = parse_parameter_specs(arguments.formula, arguments.x_column, arguments.params)
            formula_obj = ModelFormula(
                name="custom_formula",
                expression=arguments.formula,
                parameters=params,
                independent_vars=[arguments.x_column],
                dependent_var=arguments.y_column,
            )
            if arguments.backend == "matlab":
                matlab_solver = MatlabFormulaSolver(fallback_to_scipy=arguments.fallback_to_scipy)
                fit_res = matlab_solver.fit(formula_obj, x_vals, y_vals)
            else:
                scipy_solver = ScipyFormulaSolver()
                fit_res = scipy_solver.fit(formula_obj, x_vals, y_vals)
        except (CsvReadError, ModelFitError, MatlabUnavailableError, ValueError) as exc:
            parser.error(str(exc))
        print(json.dumps(fit_res.to_dict(), indent=2, sort_keys=True))
        return 0 if fit_res.converged else 2

    if arguments.command == "formula" and arguments.formula_command == "compare":
        try:
            comparison = compare_csv_models(
                arguments.path,
                objective=arguments.objective,
                x_column=arguments.x_column,
                y_column=arguments.y_column,
            )
        except (CsvReadError, ModelFitError, ValueError) as exc:
            parser.error(str(exc))
        print(json.dumps(comparison, indent=2, sort_keys=True))
        return 0

    if arguments.command == "report" and arguments.report_command == "build":
        try:
            artifacts, valid = build_csv_report(
                arguments.path,
                arguments.output_dir,
                x_column=arguments.x_column,
                y_column=arguments.y_column,
            )
        except (CsvReadError, ModelFitError) as exc:
            parser.error(str(exc))
        print(json.dumps({"valid": valid, "artifacts": artifacts.to_dict()}, indent=2))
        return 0 if valid else 2

    if arguments.command == "assistant" and arguments.assistant_command == "run":
        request = TaskRequest(
            objective=arguments.goal,
            input_path=str(arguments.path),
            x_column=arguments.x_column,
            y_column=arguments.y_column,
        )
        context_items = tuple(ContextStore(arguments.context_dir).list())
        try:
            provider = (
                JsonPlanProvider(arguments.provider_plan) if arguments.provider_plan else None
            )
            run = run_assistant(request, arguments.output_dir, context_items, provider)
        except (OSError, ValueError, ProviderPlanError) as exc:
            parser.error(str(exc))
        audit_path = save_run(run, arguments.output_dir) if arguments.mode == "audit" else None
        history_id = RunStore(arguments.history_dir).save(run)
        recommendation_id = RecommendationStore(arguments.recommendation_dir).save(
            run.recommendation, history_id
        )
        if arguments.mode == "verbose":
            print(json.dumps({"plan": [asdict(step) for step in run.plan]}, indent=2))
        assistant_output: dict[str, Any] = {
            "status": run.status,
            "objective": run.request.objective,
            "verification": asdict(run.verification),
            "recommendation": run.recommendation,
        }
        if audit_path is not None:
            assistant_output["audit_record"] = str(audit_path)
        assistant_output["run_id"] = history_id
        assistant_output["recommendation"]["recommendation_id"] = recommendation_id
        print(json.dumps(assistant_output, indent=2, sort_keys=True))
        return 0 if run.status == "success" else 2

    if arguments.command == "assistant" and arguments.assistant_command == "recommendation":
        store = RecommendationStore(arguments.recommendation_dir)
        try:
            command = arguments.recommendation_command
            if command == "list":
                print(json.dumps(store.list(), indent=2, sort_keys=True))
            elif command == "show":
                print(json.dumps(store.get(arguments.recommendation_id), indent=2, sort_keys=True))
            elif command == "accept":
                print(
                    json.dumps(
                        store.update(
                            arguments.recommendation_id, "accepted", reason=arguments.reason
                        ),
                        indent=2,
                        sort_keys=True,
                    )
                )
            elif command == "reject":
                print(
                    json.dumps(
                        store.update(
                            arguments.recommendation_id, "rejected", reason=arguments.reason
                        ),
                        indent=2,
                        sort_keys=True,
                    )
                )
            else:
                print(
                    json.dumps(
                        store.update(
                            arguments.recommendation_id,
                            "corrected",
                            corrected_action=arguments.action,
                            reason=arguments.reason,
                        ),
                        indent=2,
                        sort_keys=True,
                    )
                )
        except (FileNotFoundError, ValueError) as exc:
            parser.error(str(exc))
        return 0

    if arguments.command == "assistant" and arguments.assistant_command == "evaluate":
        try:
            if arguments.compare:
                first = json.loads(Path(arguments.compare[0]).read_text(encoding="utf-8"))
                second = json.loads(Path(arguments.compare[1]).read_text(encoding="utf-8"))
                print(json.dumps(compare_evaluations(first, second), indent=2, sort_keys=True))
                return 0
            evaluation_report = evaluate_suite(arguments.project_root, arguments.output_dir)
            path = save_evaluation(evaluation_report, arguments.output_dir)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            parser.error(str(exc))
        print(json.dumps({"report": str(path), **evaluation_report}, indent=2, sort_keys=True))
        return 0 if evaluation_report["score"] == 1.0 else 2

    if arguments.command == "assistant" and arguments.assistant_command == "context":
        context_store = ContextStore(arguments.context_dir)
        try:
            if arguments.context_command == "set":
                item = context_store.set(
                    arguments.key,
                    arguments.value,
                    kind=arguments.kind,
                    source=arguments.source,
                    confidence=arguments.confidence,
                    status=arguments.status,
                )
                print(json.dumps(item.__dict__, indent=2, sort_keys=True))
            elif arguments.context_command == "list":
                print(json.dumps(context_store.list(), indent=2, sort_keys=True))
            elif arguments.context_command == "show":
                print(json.dumps(context_store.get(arguments.key), indent=2, sort_keys=True))
            else:
                context_store.remove(arguments.key)
                print(json.dumps({"removed": arguments.key}, indent=2))
        except (FileNotFoundError, ValueError) as exc:
            parser.error(str(exc))
        return 0

    if arguments.command == "assistant" and arguments.assistant_command == "history":
        print(json.dumps(RunStore(arguments.history_dir).list(), indent=2, sort_keys=True))
        return 0

    if arguments.command == "assistant" and arguments.assistant_command == "show":
        try:
            record = RunStore(arguments.history_dir).load(arguments.run_id)
        except (FileNotFoundError, ValueError) as exc:
            parser.error(str(exc))
        print(json.dumps(record, indent=2, sort_keys=True))
        return 0

    if arguments.command == "assistant" and arguments.assistant_command == "compare":
        run_store = RunStore(arguments.history_dir)
        try:
            comparison = compare_runs(
                run_store.load(arguments.first_run), run_store.load(arguments.second_run)
            )
        except (FileNotFoundError, ValueError) as exc:
            parser.error(str(exc))
        print(json.dumps(comparison, indent=2, sort_keys=True))
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
