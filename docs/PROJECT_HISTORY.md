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

## 2026-10-18 — Phase 5 CLI and backend decision completed

- Documented the complete CLI contract, quick-start workflow, JSON outputs, report artifacts, and exit codes.
- Confirmed the workflow is non-interactive and scriptable.
- Recorded ADR 003: SciPy is the default MVP numerical backend; MATLAB is deferred.
- Completed the Phase 5 exit gate.

## 2026-10-18 — Phase 6 automated private pilot started

- Ran inspect, validate, and report workflows against both approved datasets using `.venv`.
- Functional, scientific accuracy, reproducibility, artifact, and local-only checks passed.
- Recorded runtime of approximately 0.54–0.64 seconds per command.
- Recorded peak child-process RSS of approximately 105 MB, above the original 20 MB planning target.
- Pilot status: functional pass; performance review and domain-qualified human review remain open.

## 2026-10-18 — Automated private pilot completed

- Added automated regression coverage for the complete report bundle on both approved datasets.
- Recorded ADR 004 to distinguish measured cold-start resource behavior from unverified hard targets.
- Automated pilot is complete; one domain-qualified human review remains required before release preparation.

## 2026-10-18 — Phase 7 release preparation started

- Added citation metadata, issue templates, pull-request checklist, CODEOWNERS placeholder, and release checklist.
- Expanded source-distribution contents to include examples and project governance files.
- Recorded the remaining publication blockers explicitly; repository visibility must remain private until they are resolved.
- Verified production wheel build, clean-target installation, version command, and synthetic validation workflow.
- Installed and passed strict mypy locally; the CI quality gates are now executable in the release environment.

## 2026-10-18 — Assistant Phase 1 completed

- Added the first deterministic assistant workflow around the verified SciModel engine.
- Added structured task, plan, tool-call, verification, recommendation, and audit-record contracts.
- Added the registered inspect → validate → report tool sequence.
- Added normal, verbose, and audit CLI modes with honest failure handling.
- Verified a complete synthetic-dataset run with all report artifacts and an `assistant_run.json` audit record.
- Expanded the suite to 65 passing tests.
- Deferred language-model provider integration until the deterministic workflow contract is stable.

## 2026-10-18 — Assistant Phase 2 completed

- Added versioned schemas for every assistant tool, including declared inputs and outputs.
- Added preflight request validation for goals, CSV inputs, required columns, and file existence.
- Added categorized tool errors for request, input, scientific, filesystem, and unexpected failures.
- Added tool version and exact tool inputs to each execution record.
- Verified both approved datasets through the stable Phase 2 tool contract.

## 2026-10-18 — Assistant Phase 3 completed

- Added persistent run history with content-derived IDs and one JSON record per run.
- Added history listing, run inspection, and run-comparison CLI commands.
- Added deterministic provider metadata and approval-record fields to assistant runs.
- Added recursive redaction of common secret-bearing fields before persistence.
- Verified two real runs can be stored, listed, loaded, and compared.

## 2026-10-18 — Assistant Phase 4 completed

- Added inspectable context storage for preferences, facts, and constraints.
- Added source, confidence, status, and update-time metadata.
- Added context set, list, show, and remove commands.
- Added context snapshots to each assistant run record.
- Verified context can be created, updated, inspected, used during a run, and removed.

## 2026-10-18 — Assistant Phase 5 completed

- Added evidence-linked recommendation records with rationale, benefit, effort, uncertainty, and prerequisites.
- Added recommendation persistence independent of scientific run evidence.
- Added accept, reject, and correct review outcomes.
- Added CLI commands for inspecting and reviewing recommendations.
- Verified the recommendation lifecycle through the CLI and regression tests.

## 2026-10-18 — Assistant Phase 6 completed

- Added benchmark cases for successful scientific workflows and honest input failure.
- Added scoring for planning/tool selection, execution status, verification, recommendations, and error categories.
- Added versioned machine-readable evaluation reports and case-level failure categories.
- Added evaluation comparison for regression tracking.
- Verified three benchmark cases with a score of 1.0.

## 2026-10-18 — Assistant Phase 7 completed

- Added controlled comparison of the recommended Michaelis–Menten and Hill candidates.
- Added fit metrics, uncertainty, AIC, BIC, confidence scores, and scientific rationales.
- Preserved explicit warnings against treating statistical fit as proof of physical correctness.
- Verified both candidate formulas converge on the synthetic dataset.

## 2026-10-18 — Optional provider expansion completed

- Added the `AssistantProvider` protocol for replaceable planning providers.
- Added the deterministic provider as the default tested implementation.
- Kept provider planning separate from tool execution and scientific computation.
- Deferred hosted and local language-model integrations until benchmark evidence supports them.

## 2026-10-18 — Provider integration foundation completed

- Added controlled JSON plan ingestion for externally produced provider plans.
- Added validation for provider metadata, plan steps, and registered-tool boundaries.
- Added honest provider failure handling and provider identity/version run metadata.
- Kept the deterministic planner as the default until an external provider passes evaluation.

## 2026-10-18 — Provider integration workflow defined

- Added gated workflow for baseline freeze, provider selection, adapter implementation, validation, private benchmarking, shadow mode, limited activation, and controlled improvement.
- Confirmed the deterministic planner remains authoritative until an external provider passes the benchmark and human-review gates.

## 2026-10-18 — Local-first provider setup documented

- Documented the current deployment policy: deterministic planning and
  scientific execution remain local by default.
- Added the local-first provider setup, configuration contract, activation
  gates, and security rules.
- Added architecture and end-to-end Mermaid diagrams showing planning,
  validated tool execution, verification, reporting, and feedback.
- Updated the README and status report to distinguish the implemented provider
  boundary from a model that has actually been installed or approved.
- Current verification baseline: 78 tests passed, 85.63% coverage, Ruff,
  mypy, and diff checks passing.

## 2026-10-18 — Advanced robustness fixture added

- Added a nonuniform, noisy, replicated single-condition enzyme-kinetics dataset.
- Added an extra metadata column to verify the CSV workflow tolerates non-model fields.
- Verified successful fitting, validation, reporting, and Michaelis–Menten/Hill comparison.
- Added the fixture to automated private-pilot regression coverage.

## 2026-10-18 — Dataset boundary test completed

- Added an exponential-decay negative-control dataset outside the current enzyme-kinetics scope.
- Verified structural inspection passes while Michaelis–Menten scientific validation fails with negative R².
- Added regression coverage to distinguish numerical convergence from model appropriateness.

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
