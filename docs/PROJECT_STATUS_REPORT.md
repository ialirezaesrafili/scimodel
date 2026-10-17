# SciModel — Project Status Report

**Review date:** 2026-10-17  
**Repository state:** Private prototype / documentation baseline  
**Overall status:** Phase 0 in progress; Phase 1 structure and configuration initialized

## 1. Executive status

SciModel has a clear product direction and a detailed end-to-end roadmap. The intended first product is a Python-first command-line workflow that moves from tabular experimental data to data inspection, a justified baseline model, validation, and a reproducible report.

The repository is not yet an executable project. The production-oriented configuration and package boundaries are now present, but there is no implementation, test suite, example dataset, CI workflow, or implemented CLI to evaluate.

The most important next step is therefore not adding advanced modeling features. It is selecting one scientific use case and turning it into a testable vertical slice with known expected behavior.

## 2. Confirmed inventory

| Area | Current state | Evidence | Assessment |
|---|---|---|---|
| Product vision | Defined | `README.md` | Good starting point |
| Scientific principles | Defined | `README.md` | Transparency, reproducibility, uncertainty, and human review are explicit |
| MVP direction | Proposed | `docs/SciModel_End_to_End_Project_Roadmap.md` | Narrow enough in principle, but not yet tied to a domain |
| Phase plan | Documented | Roadmap phases 0–8 | Ready to execute |
| Python package | Structure initialized | `pyproject.toml` and `src/scimodel/` boundaries | Package modules still need to be created in Phase 1 |
| CLI | Missing | No implementation | Command names remain proposals |
| Data ingestion | Missing | No source or fixtures | Must be designed around the selected dataset |
| Scientific model | Missing | No solver or model module | Cannot assess numerical correctness yet |
| Validation/reporting | Missing | No tests or report generator | Define output contracts before implementation |
| Tests/CI | Test structure initialized; CI missing | `tests/unit`, `tests/integration`, and `tests/scientific` directories | Add tests and CI before scientific claims are trusted |
| Examples/data | Missing | No `examples/` directory | Select a legal, non-confidential dataset |
| License/release files | Initial policy files present | Apache-2.0 license, contributor, security, and conduct files | Review project ownership and contact details before public release |

## 3. Current phase assessment

### Phase 0 — Define the first scientific problem: In progress

What is already understood:

- The target users are researchers and scientific learners.
- The first interface is intended to be a CLI.
- The default technical direction is Python with NumPy/pandas/SciPy.
- The first workflow should be inspect → formulate objective → fit → validate → report.
- The tool must expose uncertainty and decline unsupported conclusions.

What is still required to exit Phase 0:

1. Select one initial scientific domain.
2. Select one non-confidential or synthetic dataset.
3. Write the data dictionary, units, independent variables, outcome, and known limitations.
4. Select a baseline model and document why it is scientifically defensible.
5. Write an expert reference analysis by hand.
6. Define numerical tolerances, expected diagnostics, runtime expectations, and report contents.

Until these decisions are made, implementing a general model recommender would create functionality that cannot be scientifically evaluated.

### Phase 1 — Development foundation: Structure initialized, not complete

The repository now has project metadata, Python-version constraints, development-tool configuration, an Apache-2.0 license, contributor/security policy files, and documented package boundaries. This is a foundation milestone, not the Phase 1 exit gate: there are still no executable package modules, tests, or clean-install verification.

## 4. Phase execution plan

| Phase | Purpose | Main work | Required evidence | Current decision |
|---|---|---|---|---|
| 0. Scope and test case | Establish what “correct” means | Choose domain, dataset, model, reference analysis, and acceptance criteria | Approved one-page brief and reference analysis | **Do next** |
| 1. Foundation | Make the project installable and testable | Add modules, tests, tooling, and CI around the configured skeleton | Clean clone installs and tests pass | In progress after Phase 0 scope approval |
| 2. Data inspection | Make input behavior reliable | CSV/Excel intake, profiling, explicit transformations, fixtures | Deterministic quality report and failure tests | Only for selected data format |
| 3. First model | Prove one scientific calculation | Solver interface, baseline model, parameters, known-answer tests | Results meet declared tolerances | Avoid generic recommender initially |
| 4. Validation/reporting | Make results interpretable and reproducible | Diagnostics, uncertainty, manifests, report generation | Repeatable run with visible warnings and limitations | Required before pilot |
| 5. CLI/backend | Make the workflow usable | Freeze commands, options, exit codes; decide on MATLAB evidence | Documented non-interactive example works | SciPy remains default unless evidence changes this |
| 6. Private pilot | Test the whole workflow with users and experts | Scientific review, usability test, privacy/security review | First test report and go/no-go decision | No feature expansion before critical issues close |
| 7. Release preparation | Make the project safe to publish | License, dependency/data review, docs, history and CI review | Release checklist passes | Only after Phase 6 |
| 8. Launch/maintenance | Publish and improve responsibly | Versioned release, issues, contribution flow, maintenance policy | Tagged release and post-release plan | Future |

## 5. Work remaining, ordered by priority

### P0 — Required before implementation can be scientifically meaningful

- Choose the first research question and domain.
- Choose the reference dataset and confirm permission to use it.
- Define the target output and what an expert considers a useful result.
- Select the first model family and its assumptions.
- Define acceptance criteria and known-answer values.

### P1 — Required for the first executable vertical slice

- Create the Python package skeleton and development environment.
- Add a minimal test suite and CI.
- Implement data inspection for the selected input format.
- Implement one baseline fit with clear errors and metadata.
- Generate a machine-readable result and human-readable report.

### P2 — Required before private pilot

- Add diagnostics and uncertainty appropriate to the chosen model.
- Add reproducibility metadata and a repeated-run test.
- Document unsupported cases and data-handling behavior.
- Test with synthetic data and one permitted representative dataset.
- Review the workflow with at least one person who can judge the science.

### P3 — Defer until evidence supports expansion

- MATLAB integration.
- Additional model families and domains.
- Literature search or an AI recommendation layer.
- GUI/web interface.
- Native-code or GPU optimization.
- Public launch and broad branding work.

## 6. Immediate action list

The next work should be completed in this order:

1. Create `docs/PHASE_0_SCOPE_BRIEF.md` from the Phase 0 template below.
2. Fill in the domain, dataset, variables, units, and scientific objective.
3. Add the expert reference analysis and acceptance criteria.
4. Create the Phase 1 Python skeleton only after the scope brief is reviewable.
5. Update this report after each phase gate with links to the resulting files, tests, or decisions.

### Phase 0 scope brief template

Copy this section into `docs/PHASE_0_SCOPE_BRIEF.md` and replace every placeholder.

```text
Scientific domain:
Research question:
Target user:
Input file and permission:
Independent variables and units:
Outcome variable and units:
Number and structure of observations:
Known data-quality issues:
Baseline model:
Model assumptions:
Expected parameter/result behavior:
Reference analysis:
Numerical acceptance tolerances:
Required diagnostics:
Required report sections:
Known unsupported cases:
Reviewer:
Date approved:
```

## 7. Risks and current blockers

| Item | Type | Impact | Mitigation |
|---|---|---|---|
| No selected domain or dataset | Blocker for Phase 0 exit | The team cannot judge model suitability or numerical correctness | Choose one evaluable use case before broad implementation |
| Scope may expand into a general AI scientist | Product/scientific risk | Results become difficult to validate and explain | Enforce one workflow and explicit abstention rules |
| Private or licensed data may enter the repository | Privacy/legal risk | Public release could expose sensitive material | Use synthetic or redistributable data and review history before release |
| MATLAB assumptions may affect installation | Adoption risk | Users may be unable to reproduce the default workflow | Keep SciPy as the default; require evidence for an adapter |
| No automated tests yet | Scientific reliability risk | Numerical regressions could go unnoticed | Add known-answer tests before claiming model support |

## 8. Definition of “on track”

The project is on track when:

- Phase 0 has an approved scope brief and reference analysis.
- A clean environment can install the package and run tests.
- One selected dataset can be inspected without silent data changes.
- One selected model passes known-answer tests.
- A report states results, assumptions, diagnostics, uncertainty, limitations, and reproduction metadata.
- A private pilot has reviewed both scientific behavior and usability.

## 9. Update protocol

Update this report at every phase gate. Keep each update evidence-based:

- Change the phase status only when its exit gate has passed.
- Link to tests, reports, decisions, or datasets that support the status.
- Record unresolved issues instead of hiding them in prose.
- Separate implemented behavior from planned behavior.
- Revisit the roadmap when scientific evidence changes the scope.
