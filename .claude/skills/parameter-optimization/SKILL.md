---
name: parameter-optimization
description: Finds model parameters and operating conditions with SciPy optimizers — bounded nonlinear least squares, weighted and robust losses, multi-start and global search, convergence diagnostics, and optimal experimental design. Use when fitting or refitting a model, when a fit fails to converge or lands in a local minimum, or when choosing which measurements to take next. For multi-objective problems use the pymoo skill.
---

# Parameter and operating-condition optimization

SciPy is SciModel's default backend (ADR 003). Every solver must honour the same `FitResult` contract (parameters, SEs, CIs, metrics, convergence, evaluations, initial values).

## Choosing a method

| Problem | Method |
|---|---|
| Curve fit, bounds, smooth residuals | `scipy.optimize.least_squares(method="trf", bounds=..., x_scale="jac")` (current default) |
| Outliers suspected | same, with `loss="soft_l1"` or `"huber"` and `f_scale` ≈ noise SD — report it as a robustness check, not the primary fit |
| Known heteroscedastic noise | weighted residuals `(model - y) / sigma` |
| Multiple local minima | multi-start from a Latin hypercube inside the bounds, or `differential_evolution`, then polish with `least_squares` |
| Scalar objective (likelihood, design criterion) | `minimize(method="L-BFGS-B")` with bounds |
| Several competing objectives | `pymoo` skill |

## Good practice

1. **Initial values from physics** (e.g. Lineweaver–Burk seeds, max observed response), never arbitrary constants.
2. **Bounds from physical constraints** (`Vmax > 0`, `Km > 0`); a parameter that ends on a bound must produce a warning.
3. **Scale** parameters (`x_scale="jac"`) when magnitudes differ by orders of magnitude.
4. **Check convergence:** `result.success`, `result.status`, `nfev`, gradient norm; record all of them.
5. **Multi-start check:** refit from 10–20 starting points; if different minima give a lower RSS, report it.
6. **Uncertainty:** covariance `s²(JᵀJ)⁻¹` with t-based CIs; for strongly nonlinear or small-sample cases add profile-likelihood or bootstrap CIs.
7. **Determinism:** fix seeds for any stochastic optimizer and store them in the manifest.

## Optimal experimental design (operating conditions)

To recommend where to measure next, maximize the determinant of the Fisher information `JᵀJ` (D-optimality) over candidate design points, using the current parameter estimates. For Michaelis–Menten, informative points sit near `Km` and at high saturating concentrations. Present the result as a suggestion with its assumptions (the current estimates are only approximate).

## Testing requirements

- Known-answer test against a certified reference (e.g. Puromycin: Vmax ≈ 212.684, Km ≈ 0.06412, RSS ≈ 1195.45).
- Synthetic recovery test with known truth and fixed seed.
- Failure tests: non-convergence, parameter on a bound, singular Jacobian — each must produce a clear `ModelFitError` or warning.

See also: `pymoo`, `sensitivity-analysis`, `scimodel-testing`.
