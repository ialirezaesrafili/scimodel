# SciModel CLI Reference

The CLI is local-first, non-interactive by default, and emits JSON for workflow commands so results can be used by scripts and other tools.

## Global commands

```bash
python -m scimodel --help
python -m scimodel --version
```

## Data inspection

```bash
python -m scimodel data inspect DATA.csv
python -m scimodel data inspect DATA.csv \
  --x-column substrate_conc \
  --y-column reaction_velocity
```

The command reports row/column profiles, missing values, duplicates, numeric status, and the approved kinetics data-quality rules.

## Model fitting

```bash
python -m scimodel model fit DATA.csv
```

This fits the bounded Michaelis–Menten model and returns parameter estimates, standard errors, 95% confidence intervals, fit metrics, initialization values, and convergence metadata.

## Model validation

```bash
python -m scimodel model validate DATA.csv
```

This runs the fit and returns explicit convergence, goodness-of-fit, physical-parameter, monotonicity, and residual-diagnostic results.

## Report generation

```bash
python -m scimodel report build DATA.csv --output-dir reports/run-001
```

The output directory contains:

- `report.md` — human-readable report.
- `fit_result.json` — machine-readable model result.
- `validation.json` — checks and diagnostics.
- `run_manifest.json` — input hash, configuration, and software metadata.

## Exit codes

| Code | Meaning |
|---:|---|
| `0` | Command completed and the requested validation passed. |
| `2` | Invalid input, unsupported data, failed validation, or model failure. |
| Other non-zero | Unexpected process or environment failure. |

## Contract rules

- Commands never silently impute, remove, or transform input values.
- Workflow output is JSON unless the command explicitly writes a Markdown report.
- Input paths and output directories are supplied explicitly.
- Errors are written to stderr by the argument parser and return a non-zero status.
- Scientific claims remain limited to the documented enzyme-kinetics workflow.
