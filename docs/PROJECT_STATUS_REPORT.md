# SciModel — Project Status Report

**Review date:** 2026-10-17  
**Repository state:** Private prototype / Phase 4 validation and reporting in progress
**Overall status:** Phases 0–4 complete; Phase 5 CLI and backend decisions next

## 1. Executive status

SciModel has completed **Phase 0 — Scope and Test Case Definition**. The scientific domain (Biochemical Reaction Kinetics / Enzyme Catalysis), the baseline model (Michaelis-Menten hyperbolic rate model with non-linear least squares), reference datasets (canonical Puromycin benchmark and synthetic ground-truth dataset), and rigorous acceptance criteria (parameter tolerances, RSS bounds, diagnostics, and unsupported case rules) have been fully specified and approved.

The repository has completed Phases 1–4. The validation/reporting gate passed with measured coverage, reference-accuracy assertions, confidence intervals, reproducibility metadata, and complete report sections. The next phase is CLI usability and the optional-backend decision.

## 2. Confirmed inventory

| Area | Current state | Evidence | Assessment |
|---|---|---|---|
| Product vision | Defined | `README.md` | Clear scientific principles |
| Scientific principles | Defined | `README.md` | Transparency, reproducibility, uncertainty, and human review are explicit |
| Scope & Test Case | **Complete (Phase 0 Exit Gate Passed)** | [`docs/PHASE_0_SCOPE_BRIEF.md`](PHASE_0_SCOPE_BRIEF.md), [`docs/decisions/0001-phase-0-scientific-domain-selection.md`](decisions/0001-phase-0-scientific-domain-selection.md) | Domain, datasets, reference analysis, tolerances, and unsupported cases approved |
| Reference datasets | **Present** | [`examples/enzyme_kinetics_puromycin.csv`](../examples/enzyme_kinetics_puromycin.csv), [`examples/enzyme_kinetics_synthetic.csv`](../examples/enzyme_kinetics_synthetic.csv), [`examples/README.md`](../examples/README.md) | Canonical benchmark and synthetic ground-truth datasets documented with units and provenance |
| Python package | Phase 4 workflow implemented | `pyproject.toml`, package modules, and layered boundaries | Scientific workflow is implemented incrementally by phase |
| CLI | Data inspection and model-fit commands implemented | `src/scimodel/interfaces/cli.py` | `data inspect` and `model fit` emit structured JSON |
| Data ingestion | CSV inspection complete | `src/scimodel/adapters/csv_reader.py`, `src/scimodel/application/inspect_data.py` | CSV reader, kinetics validation, and edge cases are covered by integration tests; Excel deferred by ADR 002 |
| Scientific model | Michaelis–Menten solver implemented | `src/scimodel/domain/kinetics.py`, `src/scimodel/adapters/scipy_solver.py`, `src/scimodel/application/fit_kinetics.py` | Bounded TRF least squares passes both reference datasets |
| Validation/reporting | **Complete — Phase 4 exit gate passed** | `src/scimodel/application/validate_kinetics.py`, `src/scimodel/reporting/build_report.py` | Validation, uncertainty, reports, manifests, and coverage gate are verified |
| Tests/CI | Phase 4 tests and coverage gate added | `tests/`, `.github/workflows/ci.yml`, `pyproject.toml` | 30 tests pass locally; measured coverage is 89% with an 85% CI floor |
| License/release files | Initial policy files present | Apache-2.0 license, contributor, security, and conduct files | Configured |

## 3. Current phase assessment

### Phase 0 — Define the first scientific problem: Completed (Exit Gate Passed)

All Phase 0 requirements are satisfied:
1. **Selected domain:** Biochemical Reaction Kinetics / Enzyme Catalysis.
2. **Selected datasets:** Puromycin experimental benchmark (Treloar 1974; Bates & Watts 1988) and synthetic ground-truth dataset (`V_max=200.0, K_m=0.05`).
3. **Data dictionary:** Substrate concentration $[S]$ (`ppm` / `mM`) and reaction velocity $v$ (`counts/min^2` / `\mu mol/(L \cdot min)`).
4. **Baseline model:** Michaelis-Menten hyperbolic rate equation $v = \frac{V_{\max}[S]}{K_m + [S]}$, fitted via Trust Region Reflective non-linear least squares with physical lower bounds $[0, 0]$.
5. **Comparative baseline:** Lineweaver-Burk double reciprocal transformation for parameter initialization and error distortion diagnostics.
6. **Reference analysis & tolerances:** Certified Bates & Watts reference parameter estimates ($V_{\max} = 212.684 \pm 0.50$, $K_m = 0.06412 \pm 0.0050$, $\text{RSS} \approx 1195.45$), relative parameter error $\le 0.05\%$.
7. **Unsupported cases documented:** Negative values, $< 4$ distinct concentration levels, severe substrate inhibition, cooperativity ($n \ne 1$), and unidentifiable parameter regime ($[S]_{\max} < 0.5 K_m$).
8. **ADR recorded:** [`docs/decisions/0001-phase-0-scientific-domain-selection.md`](decisions/0001-phase-0-scientific-domain-selection.md).

### Phase 1 — Development foundation: Completed (Exit Gate Passed)

- Package metadata and dependencies configured in `pyproject.toml`.
- Layered package boundaries documented under `src/scimodel/`.
- Package modules and version metadata added without introducing scientific behavior.
- CLI boundary added with `--help` and `--version`.
- GitHub Actions workflow added for formatting, linting, type checking, tests, and coverage.
- Virtual environment is available with Python 3.14.8, pytest, NumPy, SciPy, pandas, and Ruff.
- Phase 0, Phase 1, and Phase 2 tests pass: **13 passed**.
- Ruff lint and format checks pass.
- Coverage and mypy checks are configured for CI but are not yet runnable in the current environment because `pytest-cov` and `mypy` are not installed.
- Phase 1 exit evidence: CLI boundary, CI workflow, and package structure are present.
- Phase 1 exit gate passed: package boundaries, CLI boundary, CI workflow, and local test execution are present.

### Phase 2 — Data inspection: Completed for CSV (Exit Gate Passed)

- CSV input is read through a dedicated adapter without silently changing source values.
- Column profiles include missing values, numeric status, distinct values, and basic statistics.
- Kinetics checks report missing required columns, invalid numeric values, negative values, and fewer than four concentration levels.
- Duplicate rows and constant columns are reported as warnings rather than silently removed.
- `scimodel data inspect <path>` emits structured JSON and returns a non-zero status for invalid data.
- The Puromycin reference dataset and invalid-data cases are covered by integration tests.
- Malformed rows, empty files, duplicate headers, missing values, missing files, and whitespace headers are covered.
- ADR 002 records CSV-first input and defers Excel until a concrete requirement exists.
- Phase 2 CSV exit gate passed. Excel remains a future adapter decision.

### Phase 3 — Scientific modeling: In progress

- Added the Michaelis–Menten equation as a domain function.
- Added a SciPy Trust Region Reflective least-squares solver with non-negative parameter bounds.
- Added Lineweaver–Burk initialization only; it is not used as the primary fitting method.
- Added fit metrics: RSS, RMSE, and R².
- Added covariance-based parameter standard errors.
- Added convergence status, function-evaluation count, initial parameters, and final parameters to the result contract.
- Puromycin known-answer test passes: `Vmax ≈ 212.6837`, `Km ≈ 0.0641213`, `RSS ≈ 1195.4488`.
- Synthetic ground-truth recovery test passes.
- Solver failure cases are covered for insufficient observations, insufficient concentration levels, non-finite values, and negative values.
- Invalid CLI input exits with status 2 and an actionable parser error.
### Phase 3 — Scientific modeling: Completed (Exit Gate Passed)

- The Michaelis–Menten solver passes the Puromycin and synthetic known-answer tests.
- Solver failure cases are covered for insufficient observations, insufficient concentration levels, non-finite values, and negative values.
- Invalid CLI input exits with status 2 and an actionable parser error.
- Phase 3 exit gate passed.

### Phase 4 — Validation and reproducibility: Completed (Exit Gate Passed)

- Added explicit convergence, goodness-of-fit, physical-parameter, and monotonic-prediction checks.
- Added residual diagnostics including mean, standard deviation, maximum absolute residual, and sign runs.
- Added SHA-256 input identity, configuration, software, Python, and platform metadata.
- Added `model validate` JSON output.
- Added `report build` artifacts: Markdown report, fit result JSON, validation JSON, and run manifest JSON.
- Added integration tests for validation and report artifact generation.
- Measured total test coverage at **89%** and configured an **85% minimum CI threshold**.
- Added numerical assertions for certified Puromycin standard errors and confidence-interval containment.
- Mypy remains configured but unavailable locally because the dependency download did not complete.
- Phase 4 exit gate passed: report contents, numerical accuracy, uncertainty, reproducibility, tests, and coverage are verified.

## 4. Phase execution plan

| Phase | Purpose | Main work | Required evidence | Current decision |
|---|---|---|---|---|
| 0. Scope and test case | Establish what “correct” means | Choose domain, dataset, model, reference analysis, and acceptance criteria | Approved one-page brief, reference analysis, datasets, and ADR | **Complete** |
| 1. Foundation | Make the project installable and testable | Add modules, tests, tooling, and CI around the configured skeleton | Clean clone installs and tests pass | **Complete** |
| 2. Data inspection | Make input behavior reliable | CSV intake, profiling, explicit validation, fixtures, and CLI output | Deterministic quality report and failure tests | **Complete — CSV first; Excel deferred** |
| 3. First model | Prove one scientific calculation | Solver interface, Michaelis-Menten model, parameters, known-answer tests | Results meet declared tolerances | **Complete** |
| 4. Validation/reporting | Make results interpretable and reproducible | Diagnostics, uncertainty, manifests, report generation | Repeatable run with visible warnings and limitations | **Complete** |
| 5. CLI/backend | Make the workflow usable | Freeze commands, options, exit codes; decide on MATLAB evidence | Documented non-interactive example works | **Next** — SciPy default |
| 6. Private pilot | Test the whole workflow with users and experts | Scientific review, usability test, privacy/security review | First test report and go/no-go decision | No feature expansion before critical issues close |
| 7. Release preparation | Make the project safe to publish | License, dependency/data review, docs, history and CI review | Release checklist passes | Only after Phase 6 |
| 8. Launch/maintenance | Publish and improve responsibly | Versioned release, issues, contribution flow, maintenance policy | Tagged release and post-release plan | Future |

## 5. Work remaining, ordered by priority

### P0 — Immediate Next Actions (Phase 5)

- Freeze the CLI command/option/exit-code contract.
- Add end-user CLI documentation and a complete quick-start workflow.
- Record the evidence-based MATLAB optional-backend decision.

### P1 — Later Phase Actions

- Add domain-specific diagnostics needed by the private pilot.
- Review uncertainty and report semantics with a scientific reviewer.
- Prepare the Phase 5 CLI usability and backend decision.

## 6. Risks and current blockers

| Item | Type | Impact | Mitigation | Status |
|---|---|---|---|---|
| No selected domain or dataset | Scientific blocker | Cannot evaluate numerical correctness | Enzyme kinetics & Puromycin/synthetic datasets approved in ADR 001 | **Resolved** |
| General AI scientist scope creep | Scientific risk | Results unexplainable | Strict adherence to Phase 0 Michaelis-Menten scope brief | **Mitigated** |
| Private laboratory data leakage | Legal/privacy | Exposure of confidential data | Public domain benchmark & synthetic fixtures only | **Mitigated** |
| Automated test coverage | Reliability risk | Regressions in scientific calculation | Phase 0 tests pass; install coverage/type-checking tools and add CI | **In progress** |

## 7. Definition of “on track”

The project is on track:
- Phase 0 has an approved scope brief, reference datasets, ADR 001, and reference analysis.
- Phase 0 acceptance criteria and reference behavior are guarded by automated tests.
- The current validation baseline is 30 passing tests, 89% measured coverage, and passing Ruff lint/format checks.
- Phases 1–4 are complete with 30 passing tests and 89% measured coverage.
- Phase 5 is next: CLI usability and optional-backend decisions.
