# SciModel — Project History

This document records meaningful project milestones and decisions. It complements the technical [changelog](../CHANGELOG.md): the changelog describes repository changes, while this history explains why the project moved from one phase to the next.

## 2026-10-17 — Phase 0 completed

- Selected biochemical reaction kinetics / enzyme catalysis as the first scientific domain.
- Selected the Michaelis–Menten model as the first baseline workflow.
- Added the Puromycin benchmark and a synthetic ground-truth dataset.
- Defined model assumptions, physical constraints, unsupported cases, diagnostics, and numerical acceptance criteria.
- Recorded the decision in ADR 001.
- Added eight Phase 0 scope and scientific reference tests.

## 2026-10-17 — Phase 1 foundation started

- Added Python packaging and development-tool configuration.
- Established the layered package boundaries: domain, application, adapters, infrastructure, and interfaces.
- Added the initial package metadata and version source.
- Added the top-level CLI with `--help` and `--version`.
- Added the first CI workflow for formatting, linting, type checking, tests, and coverage.
- Verified locally with 10 passing tests, Ruff linting, and Ruff formatting checks.

## 2026-10-17 — Phase 2 data inspection started

- Added a dependency-free CSV reader with explicit file, header, and row-shape errors.
- Added deterministic column profiling, missing-value, duplicate-row, constant-column, and numeric checks.
- Added the approved kinetics validation rules for non-negative values and at least four concentration levels.
- Added `scimodel data inspect <path>` with structured JSON output and non-zero exit status for invalid data.
- Added integration tests for the Puromycin dataset, CLI output, and invalid kinetics data.

## 2026-10-17 — Phase 2 CSV exit gate passed

- Added edge-case coverage for empty files, duplicate headers, malformed rows, missing values, missing files, and whitespace around headers.
- Fixed header normalization while preserving source values.
- Recorded ADR 002: CSV is the supported Phase 2 format; Excel is deferred as an optional future adapter.
- Phase 2 CSV inspection is complete with 19 passing tests.

## 2026-10-17 — Phase 3 scientific modeling started

- Added the Michaelis–Menten domain equation and a bounded SciPy TRF least-squares adapter.
- Added Lineweaver–Burk initialization while keeping nonlinear least squares as the primary fit.
- Added fit results with parameters, standard errors, RSS, RMSE, R², convergence status, and function evaluations.
- Added `scimodel model fit <path>` with structured JSON output.
- Verified the Puromycin reference fit and synthetic ground-truth recovery.
- Expanded the test suite to 23 passing tests.

## 2026-10-17 — Phase 4 validation and reproducibility started

- Added explicit model validation checks and residual diagnostics.
- Added reproducibility manifests containing input SHA-256, configuration, software, Python, and platform metadata.
- Added `model validate` and `report build` CLI commands.
- Added Markdown, JSON fit-result, JSON validation, and JSON manifest artifacts.
- Expanded the test suite to 30 passing tests.

## 2026-10-17 — Phase 4 quality gates strengthened

- Measured the repository at 89% total test coverage.
- Added an 85% minimum coverage threshold to project configuration and CI.
- Added certified standard-error and confidence-interval accuracy assertions for the Puromycin benchmark.

## 2026-10-17 — Phase 4 exit gate passed

- Confirmed the report contains data quality, model assumptions, parameter uncertainty, diagnostics, limitations, and reproduction metadata.
- Confirmed 30 tests pass with 89% measured coverage against the configured 85% minimum.
- Completed the Phase 4 validation and reproducibility milestone.

## 2026-10-17 — Phase 3 failure handling hardened

- Added solver rejection tests for insufficient observations, insufficient concentration levels, non-finite values, and negative values.
- Added CLI failure behavior coverage with exit status 2 for invalid model input.
- Expanded the test suite to 28 passing tests.

## History update rule

At each phase gate, add one dated entry containing:

1. What was completed.
2. Evidence such as tests, reports, datasets, or decisions.
3. What remains incomplete.
4. The next approved phase or action.
