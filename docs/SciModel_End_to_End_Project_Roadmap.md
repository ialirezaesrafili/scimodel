# SciModel — End-to-End Project Roadmap

**Tagline:** From experimental data to scientifically justified, validated, and reproducible models.

> A practical step-by-step plan from private repository setup through the first scientific test, a dependable CLI release, and eventual public open-source launch.

- **Working name:** SciModel (provisional; check GitHub, package-index, domain, and trademark availability before public branding).
- **Initial interface:** Command-line interface (CLI).
- **Primary language:** Python for orchestration and scientific computing.
- **Numerical backend:** SciPy-first; optional MATLAB adapter only when justified.
- **Repository status:** Private until the first test gate has passed and the owner has reviewed the results.
- **Planning horizon:** Illustrative 10–14 weeks for a focused MVP; adjust to scope and availability.

> **Execution status:** The repository is currently in **Phase 0 — scope definition**. The README and this roadmap are present, but implementation evidence has not yet been committed. See [Project Status Report](PROJECT_STATUS_REPORT.md) for the current inventory, decisions, blockers, and next actions.

---

## Executive summary

SciModel is planned as an open-source scientific modeling assistant for master's students, PhD candidates, laboratory researchers, and independent scientific innovators. Its first version should solve one end-to-end problem well: inspect a tabular experimental dataset, help the researcher formulate the modeling objective, fit a justified baseline model, evaluate its limitations, and export a reproducible result.

The project begins as a private repository. It should remain private until the first test gate has passed and the owner has reviewed scientific behavior, privacy risks, license, dependencies, and documentation. The repository can then move through a private beta before public release.

The plan intentionally avoids building a universal AI scientist in the first version. Model recommendations must be transparent, calculations must use testable numerical routines, and the tool must be able to say when the evidence is insufficient.

### Decisions to settle now

- **Name:** SciModel (provisional).
- **Interface:** CLI first; no web UI in the MVP.
- **Core language:** Python, packaged as an installable project.
- **Numerical stack:** NumPy, pandas, SciPy; add statsmodels or scikit-learn only for clearly defined use cases.
- **MATLAB:** Optional integration, not a requirement for the default installation. Use it only for a specific capability or existing workflow that justifies its installation and licensing requirements.
- **First domain:** Select one domain in which the team can assess model quality. Keep core abstractions general, but do not claim broad domain coverage prematurely.
- **First scientific workflow:** Tabular data inspection → objective clarification → baseline/model fit → diagnostics → reproducible report.

### Definition of a successful first release

- A new user can install the package in a clean environment and run the documented example.
- A sample dataset can be inspected, analyzed, validated, and reported from the CLI.
- Numerical outputs are checked against known or independently verified reference results.
- Failures, missing inputs, and unsupported cases produce clear messages rather than silent guesses.
- The run records configuration, software versions, assumptions, and limitations needed to reproduce it.
- The project has tests, documentation, a license decision, and a documented route to public release.

## Roadmap at a glance

| Phase | Focus | Exit evidence |
|---|---|---|
| 0 | Define scope and test case | One use case and success criteria agreed |
| 1 | Private repository and environment | Clean install and project skeleton |
| 2 | Data inspection | Tested CSV/Excel intake and quality report |
| 3 | First modeling workflow | Known-answer model-fitting test passes |
| 4 | Validation and reproducibility | Diagnostics, configuration, and report generated |
| 5 | CLI usability and optional backend | CLI commands work; MATLAB decision documented |
| 6 | Private pilot and evaluation | User feedback and issue log reviewed |
| 7 | Public-release preparation | Release checklist, docs, license, and CI complete |
| 8 | Public launch and maintenance | Tagged release and contribution workflow |

### Phase status at the time of this review

This status is deliberately evidence-based: a phase is not marked complete because it has been described in the roadmap.

| Phase | Status | Evidence currently available | Immediate next action |
|---|---|---|---|
| 0 — Scope and test case | **In progress** | Product goals and a proposed workflow are documented; domain, dataset, and acceptance criteria are not selected | Select one domain, dataset, reference analysis, and success criteria |
| 1 — Development foundation | **Not started** | No package metadata, source tree, tests, or CI detected | Create the installable Python skeleton and clean-environment test |
| 2 — Data inspection | **Not started** | Requirements are described only | Define input/output contracts and implement tested inspection |
| 3 — Scientific workflow | **Not started** | Model family has not been selected | Choose a baseline model and create known-answer tests |
| 4 — Validation and reproducibility | **Not started** | Requirements are described only | Define diagnostics, manifest fields, and report format |
| 5 — CLI and backend decision | **Not started** | CLI commands are proposed, not implemented | Freeze the first CLI contract; record the MATLAB decision |
| 6 — Private pilot | **Not started** | No executable workflow to pilot | Run the first test gate after Phases 1–5 |
| 7 — Public-release preparation | **Not started** | Repository is not release-ready | Complete only after the first test gate passes |
| 8 — Public launch and maintenance | **Not started** | No public release | Publish only after release acceptance criteria pass |

### How to use this roadmap

For each phase, create the listed deliverables, link the evidence from the status report or an issue, and run the exit gate before moving forward. If a phase produces a decision, record it in an ADR or in the project decision log. If a requirement is not applicable, mark it **N/A** with a reason rather than silently removing it.

---

## 1. Product scope and guardrails

The first release should be narrow enough to validate thoroughly. It should be useful as a complete workflow, not a collection of disconnected features.

### MVP includes

- A CLI with help text and clear error messages.
- CSV and Excel loading with explicit encoding, sheet, delimiter, and column handling where relevant.
- Data profiling: shape, column types, missing values, duplicate rows, summary statistics, and basic plots.
- A research-objective prompt that distinguishes explanation, parameter estimation, prediction, and simulation.
- One well-understood model family and a simple baseline; a second candidate only if scientifically appropriate.
- Parameter estimates, suitable metrics, residual diagnostics, and uncertainty information where the method supports it.
- A machine-readable run configuration and a human-readable report.
- A small set of synthetic or openly licensed example datasets and automated tests.

### Explicitly out of scope for the MVP

- A general-purpose AI agent that autonomously conducts research.
- Support for every scientific discipline, data type, or model family.
- Automatic claims that a model is physically correct or scientifically proven.
- Mandatory MATLAB installation or a requirement to own proprietary toolboxes.
- A GUI, hosted service, user accounts, collaboration platform, or distributed computing system.
- C++, Go, Rust, GPU kernels, or multiple language runtimes without a measured requirement.
- Automatic publication-ready claims or fabricated references.

### Scope rule

A feature enters the MVP only if it is necessary for the chosen end-to-end workflow, testable, and documented. Put other ideas in GitHub Issues or a future roadmap rather than expanding the initial implementation.

### Choose one initial research use case

Before implementation, choose a domain and a real but non-confidential example. Record the research question, independent variables, outcome variable, units, sample structure, expected assumptions, and how an expert would judge a useful result. If the team cannot evaluate a model recommendation, do not automate that recommendation yet.

| Field | What to write down |
|---|---|
| Research question | What relationship, parameter, prediction, or system behavior are we trying to understand? |
| Data | Source, rows, columns, units, repeated measurements, batches, and known quality issues. |
| Candidate models | At least one defensible baseline and any theory-based or empirical alternative that fits the question. |
| Reference answer | Known parameters, trusted outputs, expected qualitative behavior, or expert-reviewed result. |
| Success criteria | Numerical tolerance, diagnostic expectations, acceptable runtime, and required report contents. |

---

## 2. Phase-by-phase execution plan

### Phase 0 — Define the first scientific problem

**Indicative duration:** 2–4 days

#### Actions

1. Write a one-page product brief describing the user, the problem, the first workflow, and what the tool will not do.
2. Select one domain and one representative dataset that can legally be used in tests and examples.
3. Describe the expert-approved analysis path and at least one plausible failure mode.
4. Define measurable acceptance criteria before writing model-fitting code.
5. Interview a small number of target users if possible; record actual modeling pain points rather than feature requests alone.

**Deliverables:** Scope brief, sample dataset, data dictionary, reference analysis, success criteria, and initial risk list.

**Exit gate:** You can explain what input the CLI accepts, what result it should produce, and how you will know whether that result is correct.

### Phase 1 — Private repository and development foundation

**Indicative duration:** 2–4 days

#### Actions

1. Create a private GitHub repository named `scimodel` (subject to availability).
2. Use a supported Python version chosen and tested explicitly; record it in project metadata and CI.
3. Create the package using `pyproject.toml` and a `src/scimodel/` layout.
4. Add a virtual-environment and installation guide, `.gitignore`, formatter/linter configuration, and `pytest`.
5. Add `README.md`, a license decision placeholder or selected license, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`, and `CITATION.cff` as appropriate to project maturity.
6. Set up CI to run linting and tests on pushes and pull requests.
7. Keep secrets, credentials, private laboratory data, and licensed material out of Git.

**Deliverables:** Installable skeleton, private remote repository, automated test workflow, and reproducible developer setup.

**Exit gate:** A clean clone can be installed in a new environment and the test suite passes without relying on files from the developer's machine.

#### Suggested initial repository structure

```text
scimodel/
├── README.md
├── LICENSE
├── pyproject.toml
├── CONTRIBUTING.md
├── SECURITY.md
├── CITATION.cff
├── src/scimodel/
│   ├── cli.py
│   ├── config.py
│   ├── data/
│   ├── science/
│   ├── solvers/
│   ├── validation/
│   └── reporting/
├── tests/
├── examples/
└── docs/
```

### Phase 2 — Build reliable data inspection

**Indicative duration:** 1 week

#### Actions

1. Implement CSV and Excel readers with explicit error handling for missing files, empty files, invalid formats, and unsupported values.
2. Generate a data profile: row and column counts, inferred types, missingness, duplicate records, constant columns, and summary statistics.
3. Keep data inspection separate from data cleaning. Do not silently delete outliers, impute missing values, or change units.
4. Allow users to review and explicitly configure transformations. Record every transformation in the run configuration.
5. Add basic plots suitable for the selected data type and protect against excessive memory use on large files.
6. Write unit tests for clean data, missing values, duplicate rows, malformed input, mixed types, and empty datasets.

**Deliverables:** `data inspect` CLI command, structured data profile, test fixtures, and documentation.

**Exit gate:** Inspection output is deterministic for the same input and configuration, and data problems are reported without silently altering the source data.

### Phase 3 — Implement the first scientific model workflow

**Indicative duration:** 1–2 weeks

#### Actions

1. Define a small solver interface that describes inputs, configuration, outputs, errors, and metadata.
2. Implement one suitable baseline model using established libraries such as NumPy and SciPy.
3. Implement one additional candidate only if it answers the same scientific question and its assumptions can be compared fairly.
4. Separate data loading, model logic, validation, and CLI presentation into different modules.
5. Record parameter estimates, convergence status, warnings, solver settings, and any units or constraints relevant to interpretation.
6. Test on synthetic data with known parameters and compare against an independent reference result where feasible.
7. Document when the model is unsuitable or the data do not support a reliable fit.

**Deliverables:** Tested solver interface, model-fitting command, baseline comparison, and scientific example.

**Exit gate:** Known-answer tests pass within defined tolerances, failure cases are handled, and model assumptions are documented.

**Design principle:** Do not build a generic “choose the best model” algorithm first. Begin with explicit, reviewable rules for the chosen use case. A ranking is only meaningful when candidates are suitable for the same objective and are evaluated with a valid comparison strategy.

### Phase 4 — Validation, uncertainty, and reproducibility

**Indicative duration:** 1–2 weeks

#### Actions

1. Choose evaluation metrics that match the scientific objective; do not rely on one score alone.
2. Add residual diagnostics and checks appropriate to the model family.
3. Choose data splitting or resampling methods based on how observations were generated; account for time order, repeated samples, and experimental batches.
4. Check for data leakage and ensure preprocessing is fitted only on permitted training data when applicable.
5. Report uncertainty only where the method and data justify it; state assumptions and limitations.
6. Add optional checks for physical constraints, dimensional consistency, conservation laws, or boundary conditions where relevant to the selected domain.
7. Save a run manifest containing input file identity or checksum, configuration, package versions, solver, timestamp, and random seeds where applicable.
8. Generate a report containing methods, results, plots, diagnostics, warnings, limitations, and reproduction instructions.

**Deliverables:** Validation command, report generator, run manifest, and reproducibility test.

**Exit gate:** A user can rerun the example and understand exactly which checks passed, failed, or were not applicable.

### Phase 5 — CLI usability and backend decision

**Indicative duration:** 3–5 days

#### Actions

1. Define command names, required options, defaults, output locations, and exit codes.
2. Provide top-level help, version command, actionable error messages, and interactive prompts only when useful.
3. Support a non-interactive mode for scripts and automated workflows.
4. Decide whether MATLAB provides a specific capability the initial workflow needs. Document the decision and evidence.
5. If justified, implement MATLAB as an optional adapter with environment detection, version checks, explicit error messages, and integration tests that can be skipped when MATLAB is unavailable.
6. Keep SciPy or another open-source solver as the default path unless a real requirement says otherwise.

**Deliverables:** Documented CLI, consistent outputs and exit behavior, and a written MATLAB integration decision.

**Exit gate:** A user can complete the documented workflow from the CLI without reading internal source code. The default installation does not require MATLAB.

**MATLAB licensing and availability note:** The application may call MATLAB through the [MATLAB Engine API for Python](https://www.mathworks.com/help/matlab/matlab-engine-for-python.html), but this requires an appropriate MATLAB installation and compatible setup. Verify current MathWorks terms and prerequisites before distributing or documenting the adapter. Do not bundle MATLAB or imply that the open-source project grants a MATLAB license.

### Phase 6 — Private pilot and first test gate

**Indicative duration:** 1–2 weeks

The first test should assess scientific behavior, not just whether the program runs.

| Test type | What to verify | Evidence |
|---|---|---|
| Unit tests | Data parsing, validation rules, configuration, and error handling | Automated test results |
| Numerical tests | Known-answer fits, parameter tolerances, solver failure behavior | Reference values and tolerances |
| Scientific review | Model assumptions and diagnostics are appropriate for the chosen use case | Expert-reviewed analysis notes |
| Reproducibility | Same environment and configuration yield equivalent results within defined tolerances | Repeated-run comparison |
| Usability | A target user can install, run the example, and interpret the report | Pilot notes and issue list |
| Security/privacy | No accidental data upload, secret leakage, unsafe file handling, or execution of untrusted code | Checklist and code review |

#### Actions

1. Test on synthetic data and at least one permitted real or representative dataset.
2. Ask a small number of target users to follow the instructions without verbal help.
3. Record incorrect recommendations, confusing messages, installation failures, runtime, and memory use.
4. Classify issues as scientific correctness, data handling, usability, performance, or documentation.
5. Fix critical scientific and data-integrity issues before adding new features.
6. Record a test summary and make an explicit go/no-go decision.

**First-test exit gate:** No known critical scientific correctness or data-integrity defects remain in the tested workflow; documented numerical tolerances pass; installation and example instructions work; and limitations are visible to users.

Do not treat a successful demo as validation. The test report should include the dataset, configuration, expected behavior, actual behavior, failures, limitations, and unresolved issues.

### Phase 7 — Prepare for public open-source release

**Indicative duration:** 1 week after the test gate passes

#### Actions

1. Choose a license after deciding the reuse and contribution policy. MIT or Apache-2.0 may fit a permissive software project; review the terms before committing.
2. Review all dependencies and licenses; ensure examples, datasets, figures, and documentation may be redistributed.
3. Remove private research data, secrets, personal information, machine-specific paths, and internal notes from repository history and release artifacts.
4. Finish README sections: purpose, scope, status, installation, quick start, example, limitations, tests, and contribution instructions.
5. Add a code of conduct, contribution guide, security reporting instructions, and issue templates.
6. Run CI on supported operating systems and Python versions that you can realistically maintain.
7. Create a changelog or release notes and identify known limitations.
8. Review whether the name “SciModel” is available and sufficiently distinguishable before investing further in branding.
9. Review repository visibility, branch protection, permissions, and release contents before making it public.

**Deliverables:** Public-ready documentation, license, clean release candidate, CI results, and a release checklist.

**Exit gate:** A new user can install the project, run the example, understand the limitations, and identify how to report an issue or contribute.

#### Private-to-public transition

GitHub repository visibility can be changed when the owner is ready. Before changing it, inspect the full repository history, not only the current files. If sensitive information was ever committed, remove it properly and rotate any exposed credentials; simply deleting a file in a later commit may not remove it from history.

#### Open-source licensing note

A repository is not meaningfully open source merely because it is public. Select and include an explicit license. Keep software licensing separate from dataset, paper, and third-party material permissions. Do not add a license until the owner is comfortable with its terms.

### Phase 8 — Public launch and maintenance

**Indicative duration:** Ongoing

- Tag a versioned release and publish release notes.
- Use issues and discussions to collect bug reports, scientific-method questions, and feature proposals.
- Require tests and review for changes that affect scientific calculations.
- Maintain compatibility and dependency-update policies.
- Track known scientific limitations and publish corrections transparently.
- Archive meaningful releases and provide citation metadata when appropriate.
- Expand only after evidence: additional models, literature search, MATLAB capabilities, advanced simulations, GUI, or other languages.

---

## 3. Illustrative schedule

This is a planning estimate for a focused MVP, not a deadline guarantee. It assumes one primary developer, regular work time, and a deliberately limited first use case. If time is limited or scientific review requires more work, extend the schedule rather than skipping validation.

| Period | Main focus | Target output |
|---|---|---|
| Week 1 | Scope, use case, data and success criteria | Approved first-workflow brief |
| Week 2 | Private repo, packaging, CI, test setup | Clean installable skeleton |
| Weeks 3–4 | Data inspection and first model implementation | End-to-end analysis begins working |
| Weeks 5–6 | Validation, diagnostics, reporting, reproducibility | Scientifically testable output |
| Week 7 | CLI polish and MATLAB backend decision | Usable documented CLI |
| Weeks 8–9 | Private pilot, scientific review, bug fixes | First test report and go/no-go |
| Week 10 | Documentation, licensing, security and release prep | Release candidate |
| Weeks 11–14 | Contingency, broader platform testing, optional integrations | Public release if gates pass |

### Milestones are gates, not just dates

- **M1 — Scope approved:** chosen use case and reference analysis documented.
- **M2 — Foundation ready:** clean installation and CI work.
- **M3 — Scientific workflow works:** data inspection and model fitting produce expected outputs.
- **M4 — First test passed:** scientific, reproducibility, usability, and privacy checks reviewed.
- **M5 — Public-ready:** license, docs, release contents, and repository history reviewed.
- **M6 — Public launch:** versioned release published with a contribution path.

---

## 4. Performance policy

Do not introduce C++, Go, Rust, GPU kernels, or a second runtime simply because compiled languages are generally fast. Measure the actual workload first.

| Step | Action | Decision rule |
|---|---|---|
| 1 | Measure end-to-end runtime and memory on a representative dataset. | Identify the dominant cost before changing architecture. |
| 2 | Use appropriate algorithms and vectorized NumPy/SciPy operations. | Prefer simpler changes if they solve the bottleneck. |
| 3 | Profile hot paths and reduce repeated I/O or copies. | Optimize only measured bottlenecks. |
| 4 | Benchmark Numba, JAX, or a native extension if suitable. | Compare speed, accuracy, portability, and maintenance cost. |
| 5 | Add C++ or another backend only if evidence supports it. | Require regression tests and documented build/install behavior. |

---

## 5. Initial CLI and project conventions

### Suggested command shape

```bash
scimodel --help
scimodel --version
scimodel init my-experiment
scimodel data inspect ./data/measurements.csv
scimodel model recommend --project my-experiment
scimodel model fit --project my-experiment --model <model-name>
scimodel model validate --project my-experiment
scimodel report build --project my-experiment
```

These are proposed command names, not implemented functionality. Final names should be chosen once the workflow and output formats are clear. Commands should support machine-readable output where useful, stable exit codes, and explicit configuration.

### Project conventions to decide early

- Use type hints and documented public interfaces for core modules.
- Use a formatter and linter consistently; avoid style debates in code review.
- Keep CLI formatting out of scientific calculation functions.
- Use structured exceptions and clear user-facing errors.
- Keep configuration in a versioned, documented format such as TOML or YAML only if the chosen dependency and security implications are understood.
- Avoid executing arbitrary generated Python or MATLAB code from untrusted inputs.
- Do not upload laboratory data to external AI services unless the user explicitly opts in and the data policy is clear.
- Keep example datasets small, synthetic or redistributable, and separate from private user data.

---

## 6. Release acceptance checklist

Use this as a manual gate before calling the first release ready.

- [ ] The first user workflow and scientific objective are documented.
- [ ] The project installs in a clean environment from documented instructions.
- [ ] CLI help, version, and main workflow commands behave as documented.
- [ ] CSV/Excel input failures are handled safely and clearly.
- [ ] Data cleaning and transformations are explicit, reviewable, and recorded.
- [ ] Known-answer numerical tests pass within predeclared tolerances.
- [ ] Model assumptions and suitability limits are documented.
- [ ] Validation strategy matches the data-generation process.
- [ ] Reports distinguish measured results, assumptions, warnings, and limitations.
- [ ] Reproducibility metadata and configuration are saved.
- [ ] Automated tests run in CI and the current release candidate passes.
- [ ] No private data, credentials, or unlicensed materials are included.
- [ ] License and third-party dependency permissions are reviewed.
- [ ] README, examples, contribution guidance, and security reporting instructions are complete.
- [ ] Repository history and release artifacts are reviewed before public visibility.
- [ ] MATLAB is optional unless an explicit, documented product decision says otherwise.

> **Release rule:** If any item related to scientific correctness, data integrity, privacy, licensing, or reproducibility fails, delay the release. A smaller reliable release is preferable to a larger unvalidated one.

---

## 7. Risks and how to manage them

| Risk | Why it matters | Mitigation |
|---|---|---|
| Scope grows too quickly | Many model types and domains make correctness hard to evaluate. | One domain and one end-to-end workflow for the MVP; defer other ideas to issues. |
| Plausible but wrong recommendations | Users may trust a confident result that lacks scientific support. | Transparent rules, source verification, expert-reviewed test cases, explicit uncertainty and abstention. |
| MATLAB blocks adoption | Not every student has a compatible licensed installation. | SciPy-first default; optional adapter and documented requirements. |
| Poor reproducibility | A result cannot be independently inspected or rerun. | Run manifest, pinned dependencies, configuration, tests, and example-based reproduction checks. |
| Sensitive data exposure | Lab data may be confidential, unpublished, or regulated. | Local-first processing, no hidden uploads, safe logs, and explicit opt-in for external services. |
| Performance work too early | Native code increases maintenance and installation burden. | Benchmark first; optimize only measured bottlenecks. |
| License or data rights unclear | Public release may redistribute material without permission. | Review code, dependency, data, and paper licenses separately. |
| Name conflicts | A name may already be used by a package or project. | Check GitHub, package indexes, domains, and trademarks before public branding. |

---

## 8. After the first public release

Only expand the product after collecting evidence that the core workflow is useful and scientifically dependable.

### Potential future stages

- **Stage A — More model families:** Nonlinear models, differential equations, uncertainty quantification, and symbolic regression where the domain warrants them.
- **Stage B — Literature support:** Search for relevant papers, link claims to verifiable sources, and keep literature-derived claims separate from computed results.
- **Stage C — Solver adapters:** MATLAB or domain-specific tools for concrete workflows; C++ or other compiled components only after profiling.
- **Stage D — Better research project management:** Experiment metadata, comparison of runs, and portable project archives.
- **Stage E — Optional interface beyond CLI:** Consider a web UI only after the core package and workflow APIs are stable.
- **Stage F — Community and research evaluation:** Documented benchmark datasets, external contributions, versioned releases, and citation guidance.

### Metrics to monitor

- Installation success rate on supported platforms.
- Percentage of reference tests that pass and number of known scientific defects.
- Reproducibility of outputs under documented conditions.
- Time required for a new user to complete the example workflow.
- Number of unclear or unsupported cases correctly reported rather than silently accepted.
- User-reported usefulness of recommendations, tracked separately from numerical correctness.

---

## 9. Decisions to record in the repository

Keep a short Architecture Decision Record (ADR) whenever a decision has long-term impact. Initial ADRs should record:

- Why Python is the primary language.
- Why the CLI is the first interface.
- Why SciPy is the default numerical backend.
- Whether MATLAB integration is needed for the first workflow and why.
- Which first domain, dataset, and model family are in scope.
- How validation and uncertainty will be reported.
- What data are processed locally and whether any external service is called.
- Which license and supported platforms are selected.

---

## 10. Your next seven actions

Do these in order. Do not begin with MATLAB integration or a broad AI layer.

1. **Confirm the project identity:** Use SciModel provisionally and check for name conflicts before public branding.
2. **Create the private GitHub repository:** Use `scimodel`; set visibility to Private; do not publish it before the release gate.
3. **Choose the first scientific domain:** Pick the area where you can judge whether the model is scientifically appropriate.
4. **Choose one non-confidential dataset:** Include its data dictionary, units, and redistribution permission.
5. **Write the reference analysis:** Record how an expert would inspect the data, choose a model, validate it, and interpret the result.
6. **Define acceptance criteria:** Specify numerical tolerances, expected diagnostics, reproducibility conditions, and report requirements before implementation.
7. **Build the smallest vertical slice:** One CLI command path from data inspection to model fit, validation, and report.

### Suggested first GitHub issues

| Issue | Acceptance condition |
|---|---|
| Project skeleton | Package installs in a clean environment; CI and pytest run. |
| Data inspection | CSV/Excel profiling returns tested, deterministic output. |
| Reference dataset | Dataset permissions, units, and expected behavior documented. |
| First solver | Known-answer fit passes numerical tolerance tests. |
| Validation report | Metrics, diagnostics, assumptions, warnings, and limitations are included. |
| Reproducibility | Configuration and run metadata reproduce the example. |
| Private pilot | Pilot results and issues reviewed; go/no-go decision recorded. |

### Useful official documentation

- [Python Packaging User Guide](https://packaging.python.org/en/latest/) — packaging and distributing Python projects.
- [pytest documentation](https://docs.pytest.org/) — automated tests.
- [SciPy documentation](https://docs.scipy.org/doc/scipy/) — scientific computing and numerical methods.
- [Typer documentation](https://typer.tiangolo.com/) — type-hint-based CLI development.
- [MATLAB Engine API for Python](https://www.mathworks.com/help/matlab/matlab-engine-for-python.html) — optional MATLAB integration requirements.
- [Choose a License](https://choosealicense.com/) — compare common software licenses; verify legal and third-party material requirements before release.

---

## Final recommendation

Build SciModel as a small, private, Python-first CLI that proves one complete scientific workflow. Treat MATLAB as optional until a specific need is demonstrated. Use testable numerical methods, transparent recommendations, and reproducibility as core requirements. Pass the first scientific test before expanding scope, then review privacy, licensing, documentation, and repository history before making the project public.

This roadmap is a working plan. Update it as the first domain, user feedback, technical constraints, and scientific test results become clearer. Do not skip a validation gate just to meet an estimated week.
