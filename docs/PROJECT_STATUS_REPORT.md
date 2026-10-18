# SciModel — Project Status Report

**Review date:** 2026-10-18
**Repository state:** Private prototype / local-first provider foundation
**Overall status:** SciModel engine and assistant Phases 1–7 implemented and verified; provider integration Gates 0–2 complete

## 1. Executive status

SciModel has completed **Phase 0 — Scope and Test Case Definition**. The scientific domain (Biochemical Reaction Kinetics / Enzyme Catalysis), the baseline model (Michaelis-Menten hyperbolic rate model with non-linear least squares), reference datasets (canonical Puromycin benchmark and synthetic ground-truth dataset), and rigorous acceptance criteria (parameter tolerances, RSS bounds, diagnostics, and unsupported case rules) have been fully specified and approved.

The repository has completed the scientific engine phases and the first assistant workflow. Both approved datasets pass the functional, scientific, reproducibility, artifact, and local-only checks. The assistant now creates a plan, calls registered tools, verifies the result, saves an audit record, and recommends a next action. Release preparation still requires human scientific, legal, security, and ownership review.

## 2. Confirmed inventory

| Area | Current state | Evidence | Assessment |
|---|---|---|---|
| Product vision | Defined | `README.md` | Clear scientific principles |
| Scientific principles | Defined | `README.md` | Transparency, reproducibility, uncertainty, and human review are explicit |
| Scope & Test Case | **Complete (Phase 0 Exit Gate Passed)** | [`docs/PHASE_0_SCOPE_BRIEF.md`](PHASE_0_SCOPE_BRIEF.md), [`docs/decisions/0001-phase-0-scientific-domain-selection.md`](decisions/0001-phase-0-scientific-domain-selection.md) | Domain, datasets, reference analysis, tolerances, and unsupported cases approved |
| Reference datasets | **Present** | `examples/`, `examples/README.md` | Puromycin, synthetic ground-truth, advanced replicate, and non-kinetics control fixtures are documented |
| Python package | Phase 4 workflow implemented | `pyproject.toml`, package modules, and layered boundaries | Scientific workflow is implemented incrementally by phase |
| CLI | **Complete — Phase 5 exit gate passed** | `src/scimodel/interfaces/cli.py`, `docs/CLI_REFERENCE.md` | Commands, options, output formats, and exit codes are documented |
| Data ingestion | CSV inspection complete | `src/scimodel/adapters/csv_reader.py`, `src/scimodel/application/inspect_data.py` | CSV reader, kinetics validation, and edge cases are covered by integration tests; Excel deferred by ADR 002 |
| Scientific model | Michaelis–Menten solver implemented | `src/scimodel/domain/kinetics.py`, `src/scimodel/adapters/scipy_solver.py`, `src/scimodel/application/fit_kinetics.py` | Bounded TRF least squares passes both reference datasets |
| Validation/reporting | **Complete — Phase 4 exit gate passed** | `src/scimodel/application/validate_kinetics.py`, `src/scimodel/reporting/build_report.py` | Validation, uncertainty, reports, manifests, and coverage gate are verified |
| Tests/CI | Automated pilot and assistant evaluation coverage added | `tests/`, `.github/workflows/ci.yml`, `pyproject.toml`, `docs/PRIVATE_PILOT_REPORT.md` | 78 tests pass locally; measured coverage is 85.63%; benchmark suite scores 100% |
| Release readiness | Phase 7 in progress | `docs/RELEASE_CHECKLIST.md`, `docs/RELEASE_READINESS_REPORT.md`, `CITATION.cff`, `.github/` templates | Wheel build/install passes; publication prerequisites remain open |
| Assistant orchestration | **Phase 1 complete** | `src/scimodel/application/assistant_workflow.py`, `src/scimodel/domain/assistant.py`, assistant integration tests | Deterministic inspect → validate → report → verify workflow passes |
| Assistant tool contract | **Phase 2 complete** | Versioned schemas, preflight validation, categorized errors, audit input records | Both approved datasets pass the stable tool contract |
| Assistant run history | **Phase 3 complete** | `src/scimodel/infrastructure/run_store.py`, history CLI commands | Runs persist, redact sensitive fields, and can be compared |
| Personal/project context | **Phase 4 complete** | `src/scimodel/infrastructure/context_store.py`, context CLI commands | Context is reviewable, sourced, timestamped, and snapshotted per run |
| Recommendations | **Phase 5 complete** | `src/scimodel/infrastructure/recommendation_store.py`, recommendation CLI commands | Recommendations are evidence-linked and have reviewable outcomes |
| Evaluation | **Phase 6 complete** | `src/scimodel/evaluation/`, benchmark CLI commands | Three benchmark cases pass with a 1.0 score |
| Model comparison | **Phase 7 complete** | `src/scimodel/application/compare_models.py`, `formula compare` command | Explicit candidates can be compared with uncertainty and information criteria |
| Provider boundary | **Optional expansion complete** | `src/scimodel/domain/provider.py`, `src/scimodel/application/providers.py` | Planning is replaceable without coupling providers to scientific tools |
| Provider integration workflow | **Gates 0–2 foundation complete** | `docs/PROVIDER_INTEGRATION_WORKFLOW.md`, `docs/LOCAL_FIRST_PROVIDER_SETUP.md` | Local baseline, provider boundary, JSON-plan adapter, and rollout gates are documented |
| Deployment policy | **Local-first** | `docs/LOCAL_FIRST_PROVIDER_SETUP.md`, `docs/ARCHITECTURE.md` | No model or network provider is enabled; scientific execution remains local |
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
- Full local verification currently passes: **78 tests passed**, coverage **85.63%**.
- Ruff lint and format checks pass.
- Coverage and mypy checks are configured for CI; the current environment now passes strict mypy and the 85% coverage gate.
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

### Phase 3 — Scientific modeling: Completed (Exit Gate Passed)

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
- Strict mypy now passes after configuring NumPy/SciPy as external type-checking boundaries and targeting Python 3.12 syntax for current scientific stubs.
- Phase 4 exit gate passed: report contents, numerical accuracy, uncertainty, reproducibility, tests, and coverage are verified.

### Phase 5 — CLI usability and backend decision: Completed (Exit Gate Passed)

- Documented global commands, workflow commands, options, JSON output, report artifacts, and exit codes.
- Confirmed all workflow commands support non-interactive execution.
- Added a complete quick-start sequence to the README.
- Recorded ADR 003: SciPy is the default MVP backend; MATLAB is deferred until a concrete requirement exists.
- Phase 5 exit gate passed.

### Assistant Phase 1 — Complete (Exit Gate Passed)

- Added a structured task request, plan-step, tool-call, verification, and run-record contract.
- Added a registered tool boundary for input inspection, model validation, and report generation.
- Added deterministic inspect-first planning and honest failure recording.
- Added normal, verbose, and audit CLI modes.
- Added verification for tool order, tool success, report artifacts, and scientific validation.
- Added evidence-based recommendations for domain review or failure investigation.
- Added end-to-end tests for successful, audited, and failed assistant runs.
- The assistant does not yet use a language-model provider; that is intentionally deferred.

### Assistant Phase 2 — Complete (Exit Gate Passed)

- Added versioned schemas with explicit input and output fields for every registered tool.
- Added preflight validation for the request objective, CSV path, file existence, and column names.
- Added categorized errors and honest failed-run records.
- Added tool versions and exact tool inputs to audit records.
- Verified both approved datasets against the stable tool contract.

### Assistant Phase 3 — Complete (Exit Gate Passed)

- Added persistent one-record-per-run storage with content-derived run IDs.
- Added `assistant history`, `assistant show`, and `assistant compare` commands.
- Added deterministic planner/provider metadata and approval-record fields.
- Added recursive redaction for common secret-bearing fields before persistence.
- Verified two real runs can be stored, listed, loaded, and compared.

### Assistant Phase 4 — Complete (Exit Gate Passed)

- Added context items for preferences, facts, and constraints.
- Added source, confidence, status, and update-time metadata.
- Added context set, list, show, and remove CLI operations.
- Added context snapshots to assistant run records.
- Added explicit update and removal behavior so stored context remains user-controlled.

### Assistant Phase 5 — Complete (Exit Gate Passed)

- Added structured recommendations with evidence, rationale, benefit, effort, uncertainty, and prerequisites.
- Added recommendation persistence independent of scientific run evidence.
- Added accepted, rejected, and corrected outcome states.
- Added CLI commands for listing, inspecting, and reviewing recommendations.
- Added tests for the complete recommendation review lifecycle.

### Assistant Phase 6 — Complete (Exit Gate Passed)

- Added benchmark cases for successful workflows and honest input failure.
- Added scoring for status, tool selection, verification, recommendations, and error categories.
- Added machine-readable evaluation reports with suite and assistant versions.
- Added failure categorization and evaluation-report comparison.
- Verified the benchmark suite with three passing cases and a score of 1.0.

### Assistant Phase 7 — Complete (Controlled Extension)

- Added comparison of the recommended Michaelis–Menten and Hill candidates.
- Added AIC and BIC alongside fit metrics and parameter uncertainty.
- Preserved candidate formulas, confidence scores, rationales, and limitations.
- Added a warning that statistical criteria do not establish physical correctness.
- Verified both candidates converge on the synthetic dataset.

### Optional provider expansion — Complete

- Added an `AssistantProvider` protocol for hosted or local planning providers.
- Added the tested deterministic provider as the default implementation.
- Kept provider planning separate from tool execution and scientific computation.
- Recorded provider name and version in assistant run metadata.
- Deferred network and local language-model integrations until benchmark evidence supports them.

### Dataset boundary test — Complete

- Added an exponential-decay negative-control dataset outside the current enzyme-kinetics scope.
- Verified structural inspection can pass while Michaelis–Menten scientific validation fails.
- Added regression coverage to distinguish numerical convergence from model appropriateness.

### Provider integration foundation — Complete

- Added controlled JSON plan ingestion for externally produced provider plans.
- Added validation for provider metadata, plan steps, and registered-tool boundaries.
- Added honest provider failure handling before scientific execution.
- Kept the deterministic provider as the default fallback.

## 4. Phase execution plan

| Phase | Purpose | Main work | Required evidence | Current decision |
|---|---|---|---|---|
| 0. Scope and test case | Establish what “correct” means | Choose domain, dataset, model, reference analysis, and acceptance criteria | Approved one-page brief, reference analysis, datasets, and ADR | **Complete** |
| 1. Foundation | Make the project installable and testable | Add modules, tests, tooling, and CI around the configured skeleton | Clean clone installs and tests pass | **Complete** |
| 2. Data inspection | Make input behavior reliable | CSV intake, profiling, explicit validation, fixtures, and CLI output | Deterministic quality report and failure tests | **Complete — CSV first; Excel deferred** |
| 3. First model | Prove one scientific calculation | Solver interface, Michaelis-Menten model, parameters, known-answer tests | Results meet declared tolerances | **Complete** |
| 4. Validation/reporting | Make results interpretable and reproducible | Diagnostics, uncertainty, manifests, report generation | Repeatable run with visible warnings and limitations | **Complete** |
| 5. CLI/backend | Make the workflow usable | Freeze commands, options, exit codes; decide on MATLAB evidence | Documented non-interactive example works | **Complete — SciPy default; MATLAB deferred** |
| 6. Private pilot | Test the whole workflow with users and experts | Scientific review, usability test, privacy/security review | First test report and go/no-go decision | **Automated pass; human review pending** |
| 7. Release preparation | Make the project safe to publish | License, dependency/data review, docs, history and CI review | Release checklist passes | **In progress** |
| 8. Launch/maintenance | Publish and improve responsibly | Versioned release, issues, contribution flow, maintenance policy | Tagged release and post-release plan | Future |

## 5. Work remaining, ordered by priority

### P0 — Immediate Next Actions (Assistant Phase 7+)

- Add further model families only with new scientific acceptance criteria.
- Evaluate optional language-model provider integration against the benchmark suite.
- Keep public release blockers and domain review separate from feature development.
- Review scientific outputs with a domain-qualified reviewer.

### P0 — Phase 7 release preparation

- Verify the package build and clean installation from a built artifact.
- Replace repository-owner placeholders in URLs, CODEOWNERS, security links, and citation metadata.
- Complete final license, dependency, dataset, history, and security reviews.
- Do not change repository visibility until every release checklist blocker is resolved.

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
- The current validation baseline is 78 passing tests, 86% measured coverage, and passing Ruff lint/format checks.
- The SciModel engine phases and assistant Phases 1–7 are complete; the automated private pilot, benchmark suite, and controlled model comparison pass.
- Further expansion and release preparation remain in progress; public publication is blocked by documented checklist items.
