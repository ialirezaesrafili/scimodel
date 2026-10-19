# ADR 005: Extensible Formula Modeling, LLM Formulation, and Optional MATLAB Backend

- **Status:** Accepted
- **Date:** 2026-10-18
- **Deciders:** SciModel Architecture & Scientific Working Group

## Context

The initial MVP (Phases 0–6) established a reliable vertical slice for tabular kinetics data using a fixed Michaelis–Menten model with SciPy. To expand SciModel into a generalized scientific modeling assistant, the system must support:
1. **Dynamic / Extensible Mathematical Formulas:** Transitioning from hardcoded equations to a domain representation that can parse, validate, and evaluate arbitrary mathematical models (e.g., substrate inhibition, Hill kinetics, exponential decay, rational functions).
2. **LLM-Assisted Hypothesis Formulation:** An AI formulation step that analyzes data profiles (monotonicity, curvature, saturation, plateaus) and domain objectives, proposing candidate mathematical formulas, parameter bounds, and physical assumptions.
3. **Multi-Language Solver Support (MATLAB Engine):** Integrating MATLAB as an optional solver backend for symbolic derivation, equation solving, and curve fitting (e.g., using MATLAB's Symbolic Math Toolbox or Optimization Toolbox), while preserving SciPy as the zero-dependency open-source default.

## Decisions

1. **Domain Model Generalization (`ModelFormula`):**
   - Create a `ModelFormula` value object containing parameter definitions, variable specifications, mathematical expressions, physical bounds, and scientific assumptions.
   - Enforce an AST-based safe mathematical evaluator for Python. Prohibit `eval()` and `exec()` to prevent code injection vulnerabilities when evaluating formulas proposed by LLMs or external inputs.

2. **Decoupled Solver Architecture (`ModelSolverPort`):**
   - Define a `ModelSolverPort` protocol in the application layer.
   - Implement `ScipyFormulaSolver` as the default, fully open-source backend using `scipy.optimize.curve_fit` / `least_squares`.
   - Implement `MatlabFormulaSolver` as an optional adapter using the MATLAB Engine API for Python (`matlab.engine`). If the MATLAB runtime or licenses are unavailable, the adapter cleanly abstains or falls back to SciPy.

3. **LLM Formulation Port (`FormulaRecommenderPort`):**
   - The LLM step consumes structured JSON data profiles (from `scimodel data inspect`) and outputs a validated JSON schema containing candidate formulas, initial parameter guesses, and scientific justifications.
   - All LLM-generated formulas must pass AST validation and domain invariant checks before being handed to either numerical solver.

## Consequences

- The architecture preserves strict dependency inversion: domain logic remains independent of LLM APIs and MATLAB runtimes.
- Tests for the MATLAB adapter will automatically skip when MATLAB is not present in the local environment, ensuring CI continues to pass without proprietary licenses.
- Users gain the flexibility to formulate models via LLMs, solve them in MATLAB or SciPy, and inspect the resulting diagnostics in unified reproducible reports.
