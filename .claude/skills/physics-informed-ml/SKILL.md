---
name: physics-informed-ml
description: Incorporates physical laws, constraints and differential equations into data-driven models — constrained regression, ODE-based fitting with solve_ivp, hybrid mechanistic + ML residual models, and physics-informed neural networks (PINNs). Use when the system follows known equations or conservation laws, when data are sparse, or when a black-box model violates physical constraints.
---

# Physics-informed modeling

Use the **least complex approach that respects the physics.** Most lab datasets are small; a PINN is rarely the right first choice.

## Ladder of approaches (try in order)

1. **Mechanistic model with constraints** — the physics *is* the model; fit parameters with bounded least squares (current SciModel approach).
2. **ODE/DAE models fitted to data** — when the equations are differential:
   ```python
   from scipy.integrate import solve_ivp
   def rhs(t, y, k1, k2): ...
   def residuals(theta):
       sol = solve_ivp(rhs, (t[0], t[-1]), y0, t_eval=t, args=tuple(theta),
                       method="LSODA", rtol=1e-8, atol=1e-10)
       if not sol.success: raise ModelFitError(sol.message)
       return sol.y[0] - y_obs
   ```
   Fit with `least_squares`; check that solver tolerances are much tighter than the measurement noise.
3. **Hybrid / grey-box models** — mechanistic core plus a small ML term for the residual (e.g. Gaussian process on residuals). Report the mechanistic and hybrid fits side by side.
4. **Constraint-aware ML** — monotonic constraints (e.g. `HistGradientBoostingRegressor(monotonic_cst=...)`), non-negative outputs, or penalties for violating conservation laws.
5. **PINNs** (PyTorch or DeepXDE) — only for PDE problems, inverse problems with sparse data on a known PDE, or when the other methods cannot work. Loss = data misfit + λ·PDE residual + boundary/initial-condition terms.

## Physical checks to automate

- Sign and bounds (non-negative concentrations, rates and parameters).
- Monotonicity and asymptotes (e.g. `v → Vmax` as `[S] → ∞`).
- Conservation (mass/charge/energy balance closes within tolerance).
- Dimensional consistency (`uncertainty-and-units` / pint).
- Steady-state or initial conditions satisfied.

Each check should be a `ValidationCheck` with a pass/fail and a message, not just a comment in the report.

## PINN cautions

- Results depend strongly on λ weights, network size and collocation points; record all of them and the random seed.
- Verify against a classical numerical solution on a known case before trusting inverse estimates.
- Report uncertainty (ensembles or Bayesian variants); a single PINN fit has no error bars.
- Adds heavy dependencies (PyTorch); keep them optional and out of the default install.

See also: `parameter-optimization`, `pymc` (Bayesian ODE models), `uncertainty-and-units`.
