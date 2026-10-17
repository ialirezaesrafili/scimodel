# ADR 001: Selection of Enzyme Kinetics as Initial Scientific Domain

- **Status:** Accepted
- **Date:** 2026-10-17
- **Deciders:** SciModel Architecture & Scientific Working Group

## Context

Phase 0 of the SciModel Roadmap requires choosing exactly one scientific domain and one well-characterized experimental use case before implementing any model-fitting code. The chosen problem must satisfy several strict criteria:
1. It must have transparent, physically and mathematically justified mechanics.
2. It must have canonical, publicly verifiable reference datasets with known analytical or certified numerical solutions.
3. It must clearly demonstrate the core value proposition of SciModel: moving researchers away from naive, error-distorting linearizations (e.g. Lineweaver-Burk double reciprocal plots) toward defensible nonlinear parameter estimation with proper uncertainty reporting.
4. It must feature explicit physical constraints ($V_{\max} > 0$, $K_m > 0$, non-negative concentrations and velocities) and identifiable failure modes (e.g., substrate inhibition, unidentifiable parameters when $[S]_{\max} \ll K_m$).

### Alternatives Considered

1. **Ordinary Linear Regression (e.g., Hooke's Law / Spectrophotometry / Beer-Lambert):**
   - *Pros:* Trivial closed-form ordinary least squares (OLS) solution.
   - *Cons:* Too simple to validate nonlinear optimization, solver convergence, physical bound enforcement, or initial parameter heuristic estimators. Fails to exercise the scientific modeling assistant's unique capabilities.
2. **One-Compartment Pharmacokinetics ($C(t) = C_0 e^{-k_e t}$):**
   - *Pros:* Realistic biological problem.
   - *Cons:* Often involves time-series / longitudinal clustering or intravenous vs. oral absorption dynamics (Bateman function), which adds extra confounding data-structure dimensions for a Phase 0 MVP.
3. **Enzyme Kinetics / Michaelis-Menten:**
   - *Pros:* The canonical benchmark problem in biochemical modeling and statistical nonlinear regression (Bates & Watts 1988, NIST StRD benchmarks). Directly connects an independent variable ($[S]$) to an outcome ($v$) with two parameters ($V_{\max}, K_m$) having physical meanings, strict physical bounds, and clear asymptotic behaviors.

## Decision

We select **Biochemical Reaction Kinetics (Michaelis-Menten Enzyme Kinetics)** as the initial domain and use case for SciModel Phase 0 through Phase 6.

Specifically:
- **Baseline Model:** Michaelis-Menten hyperbolic rate equation $v = \frac{V_{\max}[S]}{K_m + [S]}$, fitted via Non-Linear Least Squares (SciPy `curve_fit` / Trust Region Reflective with bounds).
- **Comparative Baseline / Heuristic:** Lineweaver-Burk linear transformation ($1/v$ vs $1/[S]$), implemented strictly for parameter initialization and diagnostic comparison of residual distortion.
- **Reference Datasets:**
  1. The canonical Puromycin treated dataset (`examples/enzyme_kinetics_puromycin.csv`) from Treloar (1974) and Bates & Watts (1988).
  2. A deterministic synthetic ground-truth dataset (`examples/enzyme_kinetics_synthetic.csv`) with known truth ($V_{\max} = 200.0$, $K_m = 0.05$).

## Consequences

- The core domain model, ports, adapters, and data inspection routines in Phases 1–4 will be designed around 2D tabular experimental kinetics data ($[S]$ vs $v$).
- Data profiling will check for non-negative values, sufficient concentration levels ($\ge 4$), replicate consistency, and potential substrate inhibition flags.
- Numerical correctness can be verified automatically against published statistical reference standards (Bates & Watts 1988).
