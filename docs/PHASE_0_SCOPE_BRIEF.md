# SciModel — Phase 0 Scope Brief

**Status:** Approved — Phase 0 Exit Gate Passed
**Owner:** SciModel Core Development Team
**Reviewer:** Scientific Review Working Group
**Date:** 2026-10-17

## Scientific problem

- **Scientific domain:** Biochemical Reaction Kinetics / Enzyme Catalysis
- **Research question:** What are the limiting maximum rate $V_{\max}$ and Michaelis affinity constant $K_m$ governing the initial velocity of an enzyme-catalyzed reaction as a function of substrate concentration $[S]$?
- **Target user:** Laboratory researchers, biochemists, pharmacologists, and graduate students analyzing in vitro enzyme kinetics assay data.
- **Why this problem matters:** Quantifying catalytic efficiency ($k_{\text{cat}}$) and substrate affinity ($K_m$) is foundational in chemical biology, metabolic engineering, and drug discovery (assessing drug potency and enzyme inhibition). In practice, researchers frequently resort to reciprocal linearization (Lineweaver-Burk $1/v$ vs $1/[S]$), which introduces severe heteroscedastic distortion, overweighting noisy measurements at low concentrations. SciModel establishes an automated, mathematically sound nonlinear regression workflow that enforces physical bounds, validates assumptions, and estimates parameter uncertainty reliably.

## Data

- **Input file/source:**
  1. `examples/enzyme_kinetics_puromycin.csv` (Treloar 1974; Bates & Watts 1988)
  2. `examples/enzyme_kinetics_synthetic.csv` (Controlled synthetic benchmark)
- **Permission to use:** Public domain (Puromycin) and open-source project fixture under Apache-2.0 (synthetic benchmark).
- **Independent variables and units:**
  - `substrate_conc`: Substrate concentration $[S]$ in $\text{ppm}$ (for Puromycin) or $\text{mM}$ (for synthetic).
- **Outcome variable and units:**
  - `reaction_velocity`: Initial reaction velocity $v$ in $\text{counts}/\text{min}^2$ (for Puromycin) or $\mu\text{mol} / (\text{L} \cdot \text{min})$ (for synthetic).
- **Number and structure of observations:**
  - Puromycin: 12 rows across 6 concentration levels (0.02, 0.06, 0.11, 0.22, 0.56, 1.10) with replicate pairs.
  - Synthetic: 14 rows across 7 concentration levels (0.01, 0.02, 0.05, 0.10, 0.20, 0.50, 1.00) with duplicate measurements.
- **Known data-quality issues:**
  - Measurement noise at low $[S]$ where relative error is amplified.
  - Risk of negative values caused by baseline subtraction noise in spectrophotometric/microplate readers.
  - Potential outliers or plate-edge artifacts in raw experimental microplates.
- **Expected data transformations:**
  - No silent transformations.
  - Raw concentrations and velocities are ingested as-is without silent imputation, outlier removal, or unit re-scaling.
  - The model workflow performs reciprocal calculations strictly for the Lineweaver-Burk diagnostic baseline, preserving original units for all nonlinear fits and reported estimates.

## Modeling plan

- **Baseline model:**
  Michaelis-Menten hyperbolic rate model:
  $$v([S]) = \frac{V_{\max} [S]}{K_m + [S]}$$
  Fitted using non-linear least squares (Trust Region Reflective algorithm via SciPy `scipy.optimize.curve_fit`) with explicit lower parameter bounds $V_{\max} > 0$, $K_m > 0$.
- **Optional comparison model:**
  Lineweaver-Burk linear transformation ($1/v = \frac{K_m}{V_{\max}} \frac{1}{[S]} + \frac{1}{V_{\max}}$) fitted via Ordinary Least Squares (OLS).
  *Purpose:* Used strictly as a comparative diagnostic baseline to demonstrate residual distortion and to provide robust initial parameter estimates ($V_{\max,0} = 1/\beta_0$, $K_{m,0} = \beta_1 / \beta_0$).
- **Model assumptions:**
  1. *Quasi-steady-state assumption:* The enzyme-substrate complex $[ES]$ concentration is stationary during the initial measurement window.
  2. *Substrate excess:* $[S]_0 \gg [E]_0$, so that substrate depletion is negligible during the initial velocity phase ($< 5\%$).
  3. *Irreversible product formation:* The step $ES \to E + P$ is irreversible over initial velocity measurements.
  4. *Homoscedastic additive Gaussian errors* in reaction velocity measurements $v$.
  5. *Monotonic saturation:* No positive/negative cooperativity (Hill coefficient $n = 1$) and no substrate inhibition at high $[S]$.
- **Constraints or physical rules:**
  1. $V_{\max} > 0$: Maximum reaction velocity must be strictly positive.
  2. $K_m > 0$: Michaelis constant (substrate concentration at $v = V_{\max}/2$) must be strictly positive.
  3. $[S] \ge 0$: Substrate concentration cannot be negative.
  4. $v \ge 0$: Initial reaction rate cannot be negative.
  5. *Asymptotic saturation:* $\lim_{[S] \to \infty} v([S]) = V_{\max}$, and $\frac{\partial v}{\partial [S]} > 0$ for all $[S] \ge 0$.
- **Expected parameter/result behavior:**
  - At $[S] = K_m$, $v = V_{\max}/2$.
  - At $[S] \ll K_m$, reaction is pseudo-first-order: $v \approx \frac{V_{\max}}{K_m} [S]$.
  - At $[S] \gg K_m$, reaction is pseudo-zero-order: $v \approx V_{\max}$.

## Reference analysis and acceptance criteria

### Reference analysis steps
1. **Data profiling:** Validate column schema, detect non-negative invariants, ensure $\ge 4$ unique concentration levels, and quantify replicate variance.
2. **Heuristic initialization:** Compute initial parameter seeds ($V_{\max,0}, K_{m,0}$) via ordinary least squares on Lineweaver-Burk reciprocal coordinates.
3. **Bounded NLLS Optimization:** Fit Michaelis-Menten rate equation via Trust Region Reflective optimization with lower bounds $[0, 0]$.
4. **Covariance & Uncertainty:** Derive parameter standard errors $\text{SE}(V_{\max}), \text{SE}(K_m)$ from the covariance matrix $(J^T J)^{-1} s^2$, and compute studentized $95\%$ confidence intervals.
5. **Diagnostics:** Evaluate $R^2$, Root Mean Square Error (RMSE), Residual Sum of Squares (RSS), and residual runs test for curvature/heteroscedasticity.
6. **Artifact Generation:** Output structured JSON manifest and markdown report detailing findings, diagnostics, limitations, and environment metadata.

### Numerical acceptance

- **Known-answer values:**
  - *Puromycin Treated Benchmark (Bates & Watts 1988 reference):*
    - $V_{\max} = 212.684 \pm 0.50\ \text{counts}/\text{min}^2$
    - $K_m = 0.06412 \pm 0.0050\ \text{ppm}$
    - Residual Sum of Squares (RSS): $1195.45 \pm 5.0$
  - *Synthetic Ground-Truth Benchmark:*
    - Ground truth: $V_{\max}^* = 200.00$, $K_m^* = 0.050$
    - Estimated parameters within $95\%$ confidence bounds ($V_{\max} \in [190.0, 210.0]$, $K_m \in [0.040, 0.060]$)
- **Allowed parameter error:** Relative error $\le 0.05\%$ compared to standard SciPy/R certified non-linear solver output.
- **Allowed prediction/error metric:** $R^2 > 0.95$ for reference test data; RMSE consistent with replicate noise floor.
- **Expected convergence behavior:** Optimizer terminates with convergence flag (`ier` in `[1, 2, 3, 4]` / `success == True`) in $< 25$ iterations.
- **Runtime/memory expectation:** Execution time $< 100\ \text{ms}$ on reference dataset; peak memory $< 20\ \text{MB}$.

### Required report contents

- [x] Input summary and data-quality warnings
- [x] Model, assumptions, and configuration
- [x] Parameter estimates/results and units
- [x] Metrics and diagnostics
- [x] Uncertainty, where justified
- [x] Limitations and unsupported conclusions
- [x] Reproduction instructions and software metadata

## Unsupported cases

List cases the first version must reject or clearly mark as unsupported:

1. Negative concentrations ($[S] < 0$) or negative velocities ($v < 0$).
2. Datasets with fewer than 4 distinct concentration levels (insufficient degrees of freedom).
3. Severe substrate inhibition (where velocity drops systematically by $> 25\%$ at high $[S]$).
4. Sigmoidal kinetics exhibiting cooperative binding (Hill coefficient $n \ne 1$).
5. Datasets lacking saturation where $[S]_{\max} < 0.5 \times K_m$ (unidentifiable $V_{\max}$ and $K_m$).

## Approval gate

Phase 1 may begin because the domain, dataset, model, reference analysis, and acceptance criteria are complete and reviewed. Preserve this approved scope as the implementation baseline.

- **Approved by:** SciModel Core Architecture & Scientific Working Group
- **Approval date:** 2026-10-17
- **Related issue/decision:** ADR 001 (`docs/decisions/0001-phase-0-scientific-domain-selection.md`)
