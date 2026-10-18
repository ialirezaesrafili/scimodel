"""Command-line entry point for SciModel."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

from scimodel import __version__
from scimodel.adapters.csv_reader import CsvReadError
from scimodel.application.fit_kinetics import fit_csv
from scimodel.application.inspect_data import inspect_csv
from scimodel.application.validate_kinetics import validate_csv
from scimodel.domain.fit import ModelFitError
from scimodel.reporting.build_report import build_csv_report


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
                arguments.path,
                x_column=arguments.x_column,
                y_column=arguments.y_column,
            )
        except CsvReadError as exc:
            parser.error(str(exc))
        print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
        return 0 if report.valid else 2
    if arguments.command == "model" and arguments.model_command == "fit":
        try:
            result = fit_csv(
                arguments.path,
                x_column=arguments.x_column,
                y_column=arguments.y_column,
            )
        except (CsvReadError, ModelFitError) as exc:
            parser.error(str(exc))
        print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
        return 0 if result.converged else 2
    if arguments.command == "model" and arguments.model_command == "validate":
        try:
            result, validation = validate_csv(
                arguments.path,
                x_column=arguments.x_column,
                y_column=arguments.y_column,
            )
        except (CsvReadError, ModelFitError) as exc:
            parser.error(str(exc))
        output = {"fit": result.to_dict(), "validation": validation.to_dict()}
        print(json.dumps(output, indent=2, sort_keys=True))
        return 0 if validation.valid else 2
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
