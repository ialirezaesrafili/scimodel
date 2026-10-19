---
name: sensitivity-analysis
description: Determines which parameters and inputs most influence model outputs — local derivatives, normalized sensitivity coefficients, parameter correlation/identifiability, and global variance-based methods (Sobol, Morris) with SALib. Use when asked which parameters matter, whether parameters are identifiable, or how uncertainty in inputs propagates to predictions.
---

# Sensitivity analysis

Answer two different questions and keep them separate in reports:

1. **Local sensitivity / identifiability** — around the fitted parameters, how strongly does the output respond, and can the data pin each parameter down?
2. **Global sensitivity** — across a plausible parameter or input range, which factors drive output variance?

## 1. Local sensitivity (always do first; no new dependencies)

Use the Jacobian already returned by `scipy.optimize.least_squares` (`result.jac`).

- **Normalized sensitivity coefficient:** `S_ij = (∂y_i/∂θ_j) · θ_j / y_i` (dimensionless; compare across parameters).
- **Parameter correlation:** from covariance `C = s² (JᵀJ)⁻¹`, `corr_jk = C_jk / sqrt(C_jj C_kk)`. |corr| > 0.95 signals that the parameters are practically non-identifiable together.
- **Condition number** of `JᵀJ`: very large values (> 1e8 after scaling) mean an ill-posed fit.
- **Profile likelihood** (more robust than the covariance for nonlinear models): fix one parameter on a grid, refit the others, plot ΔRSS; a flat profile means non-identifiable.

For Michaelis–Menten: if `[S]max < 0.5·Km`, sensitivity to `Vmax` and `Km` collapses into their ratio — exactly SciModel's "unidentifiable" unsupported case. Use this analysis to implement and test that check.

## 2. Global sensitivity (SALib)

```bash
uv pip install SALib
```

```python
from SALib.sample import sobol as sobol_sample
from SALib.analyze import sobol
problem = {"num_vars": 2, "names": ["vmax", "km"], "bounds": [[150, 250], [0.02, 0.12]]}
X = sobol_sample.sample(problem, 1024, seed=0)
Y = np.array([model(S_grid, *row).mean() for row in X])
Si = sobol.analyze(problem, Y, seed=0)  # S1, ST with confidence intervals
```

- **Morris** (elementary effects) for cheap screening of many factors.
- **Sobol** for first-order (S1) and total (ST) indices; ST − S1 large means interactions.
- Justify the bounds (from confidence intervals, literature or physical limits) and record them in the manifest.

## Reporting

- Table: parameter, estimate, SE, normalized sensitivity, correlation flags, S1/ST if computed.
- State the conclusion in plain words ("Km is poorly constrained because no concentrations exceed Km").
- Fix seeds and sample sizes; report index confidence intervals.

## Guardrails

- Local results are only valid near the fit; do not generalize them across regimes.
- Sobol indices depend entirely on the chosen input distributions — never present them without the bounds.

See also: `uncertainty-and-units`, `statistical-analysis`, `parameter-optimization`.
