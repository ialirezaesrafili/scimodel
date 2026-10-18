# SciModel

**From experimental data to reliable scientific models.**

SciModel is an open-source scientific modeling assistant designed to help master's students, PhD candidates, laboratory researchers, and independent scientific innovators transform experimental data into scientifically justified, validated, and reproducible mathematical models.

The project addresses a common challenge in scientific research: researchers often collect valuable experimental data but lack a clear, systematic workflow for choosing appropriate mathematical models, estimating parameters, evaluating assumptions, validating results, and determining the next steps in their analysis.

SciModel aims to make this process more accessible through a command-line interface that combines scientific data analysis, mathematical modeling, numerical computation, and evidence-based model evaluation.

## Project goals

- Inspect experimental datasets and identify potential data-quality issues.
- Guide researchers in selecting suitable mathematical, statistical, and computational models.
- Support model fitting, parameter estimation, numerical optimization, and equation discovery where appropriate.
- Evaluate model performance, uncertainty, assumptions, and limitations.
- Provide transparent explanations for modeling recommendations.
- Preserve code, configurations, parameters, and results for reproducible research.
- Support extensible scientific solver backends, with Python as the primary scientific engine and optional MATLAB integration.

## Development approach

The initial release will focus on a Python-based command-line interface and a small, testable scientific workflow. The first objective is to establish a reliable end-to-end process for inspecting experimental data, fitting an appropriate model, evaluating its limitations, and generating reproducible outputs.

MATLAB integration and more advanced scientific capabilities will be introduced when specific research workflows justify them.

## Scientific principles

SciModel prioritizes scientific transparency, reproducibility, appropriate model selection, and honest reporting of uncertainty.

The application is intended to support scientific reasoning rather than replace it. Automated recommendations must be evaluated against the available evidence, and the software must clearly communicate when the data are insufficient to support a reliable conclusion.

## Project status

Early development — private prototype.

The initial release is intended for testing and evaluation before the project is made publicly available.

For the detailed execution plan and evidence-based progress tracking, see:

- [End-to-End Project Roadmap](docs/SciModel_End_to_End_Project_Roadmap.md)
- [Project Status Report](docs/PROJECT_STATUS_REPORT.md)
- [Architecture Guide](docs/ARCHITECTURE.md)
- [Local-First Provider Setup](docs/LOCAL_FIRST_PROVIDER_SETUP.md)
- [Provider Integration Workflow](docs/PROVIDER_INTEGRATION_WORKFLOW.md)
- [Development Guide](docs/DEVELOPMENT.md)
- [CLI Reference](docs/CLI_REFERENCE.md)

## Repository structure

```text
scimodel/
├── src/scimodel/
│   ├── domain/          # Scientific concepts and invariants
│   ├── application/     # Use cases and ports
│   ├── adapters/        # External-to-domain translations
│   ├── infrastructure/  # Filesystem, config, persistence, integrations
│   └── interfaces/      # CLI and presentation boundaries
├── tests/
│   ├── unit/
│   ├── integration/
│   └── scientific/
├── examples/             # Synthetic or redistributable examples only
├── data/                 # Data policy and local-data boundary
├── docs/
├── pyproject.toml
└── LICENSE
```

The architecture boundaries are configured, and the Phase 0 reference datasets, data-inspection workflow, and initial scientific fitting workflow are present. Further capabilities will be added phase by phase while preserving these boundaries.

## Quick start

```bash
# 1. Inspect data quality
python -m scimodel data inspect examples/enzyme_kinetics_puromycin.csv

# 2. Get formula recommendations based on data and research objectives
python -m scimodel formula recommend examples/enzyme_kinetics_puromycin.csv --objective "enzyme kinetics"

# 3. Fit an extensible formula with SciPy (or MATLAB adapter)
python -m scimodel formula fit examples/enzyme_kinetics_puromycin.csv \
  --formula "(Vmax * substrate_conc) / (Km + substrate_conc)" \
  --params "Vmax:0:inf,Km:0:inf" \
  --backend scipy

# 4. Validate model assumptions and generate full reproducible reports
python -m scimodel model validate examples/enzyme_kinetics_puromycin.csv
python -m scimodel report build examples/enzyme_kinetics_puromycin.csv --output-dir reports/run-001

# 5. Run the Phase 1 assistant workflow with an audit record
python -m scimodel assistant run examples/enzyme_kinetics_puromycin.csv \
  --goal "Analyze this enzyme-kinetics dataset and recommend the next action" \
  --mode audit --output-dir reports/assistant-run
```

See the [CLI Reference](docs/CLI_REFERENCE.md) for command contracts and exit codes.

The assistant currently uses a deterministic plan and the verified SciModel
tools. It inspects the input, validates the model, builds a reproducible report,
verifies the result, and recommends the next action. Provider integration is
local-first and opt-in; no hosted or local language model is enabled yet.

## Long-term vision

To build a community-driven scientific modeling platform that helps researchers across disciplines move from experimental observations to better-founded mathematical models and reproducible scientific discoveries.
