"""Command-line entry point for SciModel."""

from __future__ import annotations

import argparse
import json
import re
from collections.abc import Sequence
from pathlib import Path

import numpy as np

from scimodel import __version__
from scimodel.adapters.csv_reader import CsvReadError, read_csv
from scimodel.adapters.matlab_solver import MatlabFormulaSolver, MatlabUnavailableError
from scimodel.adapters.scipy_formula_solver import ScipyFormulaSolver
from scimodel.application.fit_kinetics import fit_csv
from scimodel.application.inspect_data import inspect_csv
from scimodel.application.recommender import RuleBasedFormulaRecommender
from scimodel.application.validate_kinetics import validate_csv
from scimodel.domain.fit import ModelFitError
from scimodel.domain.formula import _ALLOWED_FUNCTIONS, ModelFormula, ParameterSpec
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
    reserved = set(_ALLOWED_FUNCTIONS.keys()) | {independent_var}
    param_names = sorted(tokens - reserved)
    return [ParameterSpec(name, lower_bound=0.0, upper_bound=float("inf")) for name in param_names]


def build_parser() -> argparse.ArgumentParser:
    """Build the top-level SciModel argument parser."""
    parser = argparse.ArgumentParser(
        prog="scimodel",
        description="A transparent and reproducible scientific modeling assistant.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
        help="Show the installed SciModel version and exit.",
    )
    subparsers = parser.add_subparsers(dest="command")

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

    # report build
    report_parser = subparsers.add_parser("report", help="Build reproducible reports.")
    report_subparsers = report_parser.add_subparsers(dest="report_command", required=True)
    build_parser = report_subparsers.add_parser("build", help="Build a validation report bundle.")
    build_parser.add_argument("path", type=Path, help="Path to the CSV dataset.")
    build_parser.add_argument("--output-dir", type=Path, required=True)
    build_parser.add_argument("--x-column", default="substrate_conc")
    build_parser.add_argument("--y-column", default="reaction_velocity")

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the SciModel CLI and return a process exit code."""
    parser = build_parser()
    arguments = parser.parse_args(argv)

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

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
