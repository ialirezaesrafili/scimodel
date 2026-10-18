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

## Formula recommendations

```bash
python -m scimodel formula recommend DATA.csv --objective "enzyme kinetics"
```

Suggests candidate mathematical formulas based on data profiles and research objectives (e.g., enzyme kinetics, exponential decay). Returns a JSON list of candidate formulas, expressions, parameters, confidence scores, scientific rationales, and underlying physical assumptions.

Supported arguments:
- `path` — Path to CSV dataset.
- `--objective` — Scientific research objective (default: `"enzyme kinetics"`).
- `--x-column` — Independent variable column name (default: `substrate_conc`).
- `--y-column` — Dependent variable column name (default: `reaction_velocity`).

## Extensible formula fitting (SciPy & MATLAB)

```bash
python -m scimodel formula fit DATA.csv \
  --formula "(Vmax * substrate_conc) / (Km + substrate_conc)" \
  --params "Vmax:0:inf,Km:0:inf" \
  --backend scipy
```

Fits an arbitrary mathematical expression against experimental data using either the zero-dependency open-source SciPy solver or an external MATLAB engine session.

Supported arguments:
- `path` — Path to CSV dataset.
- `--formula` — Mathematical expression parsed and evaluated via safe AST validation (operators `+`, `-`, `*`, `/`, `**` and functions `exp`, `log`, `log10`, `sqrt`, `sin`, `cos`, `tanh`, `abs`).
- `--params` — Optional parameter specifications formatted as `name:min:max` or `name:min:max:init` (e.g. `"Vmax:0:inf,Km:0:inf"`).
- `--backend` — Optimization engine (`scipy` [default] or `matlab`).
- `--fallback-to-scipy` — If `--backend matlab` is chosen but MATLAB is not installed or unlicensed, gracefully fall back to SciPy.
- `--x-column` — Independent variable column name (default: `substrate_conc`).
- `--y-column` — Dependent variable column name (default: `reaction_velocity`).

The command returns parameter estimates, asymptotic standard errors, 95% confidence intervals, and fit metrics ($R^2$, RMSE, AIC, BIC).

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
