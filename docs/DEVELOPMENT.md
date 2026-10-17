# Development Guide

## Local setup

The project is configured for Python 3.11–3.13 and an isolated virtual environment. Install development dependencies with the project package manager of choice using the `dev` optional dependency group from `pyproject.toml`.

## Quality gates

Before merging implementation, the project should run:

- Ruff linting and formatting checks.
- Strict mypy type checking.
- Pytest with strict configuration.
- Coverage reporting for scientific and application logic.

The exact commands will be documented after the first package modules and test fixtures exist.

## Data policy

Use synthetic or redistributable data in `examples/`. Keep private and generated data outside version control. Every example must include units, provenance, license/permission, and expected behavior.
