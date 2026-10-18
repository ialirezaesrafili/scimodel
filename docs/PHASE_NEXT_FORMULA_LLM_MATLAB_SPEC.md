# SciModel Next Phase Specification: Extensible Formula Modeling, LLM Formulation, and MATLAB Backend

**Status:** Design Approved  
**Version:** Next-Gen Architecture (Phase 8+ / Extension Milestone)  
**Author:** SciModel Architecture & Scientific Working Group  
**Date:** 2026-10-18  

---

## 1. Executive Summary

To elevate SciModel from a single-model prototype into a generalized scientific modeling platform, this phase expands the core architecture to support:
1. **Extensible Mathematical Formulas:** Dynamic representation and evaluation of arbitrary scientific equations without hardcoding.
2. **LLM-Driven Hypothesis Formulation:** An intelligent formulation layer that reads experimental data profiles (from `scimodel data inspect`), queries an LLM with domain context, and proposes candidate equations, parameter bounds, and physical assumptions.
3. **Multi-Language Solver Backends (MATLAB & SciPy):** A pluggable solver interface allowing models to be solved either via open-source SciPy (default) or through an optional **MATLAB Engine adapter** (for researchers utilizing MATLAB's Symbolic Math, Optimization, or Curve Fitting toolboxes).

```text
┌──────────────────────┐
│  Experimental Data   │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  Data Profiling      │ (Phase 2 CSV Inspection)
│  & Quality Analysis  │
└──────────┬───────────┘
           │ Data Profile & Research Objective
           ▼
┌──────────────────────┐
│  LLM Formulation     │ Proposes candidate formulas,
│  Assistant (Port)    │ physical bounds, and assumptions
└──────────┬───────────┘
           │ Candidate Formula Spec (JSON)
           ▼
┌──────────────────────┐
│  Domain Formula      │ AST validation, parameter bounds,
│  & Safety Validation │ and mathematical invariant checks
└──────────┬───────────┘
           │
           ├───────────────────────────────┐
           ▼                               ▼
┌──────────────────────┐        ┌──────────────────────┐
│  SciPy Solver        │        │  MATLAB Engine       │
│  (Default Backend)   │        │  (Optional Adapter)  │
└──────────┬───────────┘        └──────────┬───────────┘
           │                               │
           └───────────────┬───────────────┘
                           │ Parameter Estimates, Covariance, Diagnostics
                           ▼
┌──────────────────────────────────────────┐
│  Model Validation & Reproducible Report  │ (Phase 4 Artifacts)
└──────────────────────────────────────────┘
```

---

## 2. Domain Layer: Generic Mathematical Formula (`ModelFormula`)

### 2.1 Value Objects

```python
from dataclasses import dataclass, field
from typing import Sequence


@dataclass(frozen=True)
class ParameterSpec:
    """Specification for a formula parameter."""

    name: str
    lower_bound: float = 0.0
    upper_bound: float = float("inf")
    initial_guess: float | None = None
    units: str | None = None
    description: str | None = None


@dataclass(frozen=True)
class ModelFormula:
    """Mathematical formula model representation."""

    name: str
    expression: str  # e.g., "(Vmax * s) / (Km + s)" or "Vmax * (1 - exp(-k * t))"
    parameters: Sequence[ParameterSpec]
    independent_vars: Sequence[str] = ("substrate_conc",)
    dependent_var: str = "reaction_velocity"
    latex_equation: str | None = None
    assumptions: Sequence[str] = field(default_factory=tuple)
    limitations: Sequence[str] = field(default_factory=tuple)
```

### 2.2 AST-Based Safe Mathematical Evaluator

To prevent arbitrary code execution vulnerabilities when formulas originate from external files or LLM responses:
- Python `eval()` and `exec()` are **strictly prohibited**.
- Mathematical expressions are parsed into an Abstract Syntax Tree (`ast.parse`) and evaluated using a secure whitelist:
  - Binary Operators: `Add`, `Sub`, `Mult`, `Div`, `Pow`
  - Unary Operators: `USub`, `UAdd`
  - Functions: `exp`, `log`, `log10`, `sqrt`, `sin`, `cos`, `tanh`, `abs`
  - Symbols: only declared parameter names and independent variable names are permitted.

---

## 3. Application Layer: Ports & Use Cases

### 3.1 Model Solver Port (`ModelSolverPort`)

```python
from typing import Protocol
import numpy.typing as npt
import numpy as np
from scimodel.domain.fit import FitResult


class ModelSolverPort(Protocol):
    """Port for numerical model solvers."""

    @property
    def backend_name(self) -> str: ...

    def is_available(self) -> bool:
        """Check if backend runtime and required licenses are present."""
        ...

    def fit(
        self,
        formula: ModelFormula,
        x: npt.NDArray[np.float64],
        y: npt.NDArray[np.float64],
    ) -> FitResult:
        """Fit formula parameters to data and return unified FitResult."""
        ...
```

### 3.2 LLM Formulation Recommender Port (`FormulaRecommenderPort`)

```python
from typing import Protocol
from scimodel.domain.data_quality import InspectionReport


@dataclass(frozen=True)
class FormulaRecommendation:
    formula: ModelFormula
    confidence_score: float
    scientific_rationale: str
    suggested_diagnostics: Sequence[str]


class FormulaRecommenderPort(Protocol):
    """Port for AI/LLM mathematical formulation assistants."""

    def recommend_candidates(
        self,
        inspection: InspectionReport,
        objective: str,
        domain_name: str | None = None,
    ) -> Sequence[FormulaRecommendation]:
        """Propose mathematically and scientifically sound candidate formulas."""
        ...
```

---

## 4. Adapters Layer: Implementation Details

### 4.1 SciPy Formula Solver (`ScipyFormulaSolver`)
- Implements `ModelSolverPort` using `scipy.optimize.least_squares` (TRF method) or `scipy.optimize.curve_fit`.
- Translates `ModelFormula.expression` into a vectorized callable via AST evaluation.
- Derives parameter standard errors from the Jacobian: $\text{Cov} = (J^T J)^{-1} \frac{\text{RSS}}{N - P}$.
- Always available without external runtime dependencies.

### 4.2 MATLAB Engine Adapter (`MatlabFormulaSolver`)
- Uses MathWorks' official `matlab.engine` Python API.
- **Availability Check:** Attempts to import `matlab.engine` and test for an active engine or valid license. If unavailable, `is_available()` returns `False`.
- **Expression Translation:** Translates AST expressions into vectorized MATLAB anonymous function syntax:
  $$\text{Python: } \texttt{(Vmax * s) / (Km + s)} \implies \text{MATLAB: } \texttt{@(p, s) (p(1) .* s) ./ (p(2) + s)}$$
- **Fitting Execution:** Calls MATLAB's `lsqcurvefit` or `fitnlm` (from the Statistics and Machine Learning Toolbox) or custom Levenberg-Marquardt optimizer:
  ```matlab
  opts = optimoptions('lsqcurvefit', 'Display', 'off');
  [p_fit, resnorm, residual, exitflag, output, lambda, jacobian] = ...
      lsqcurvefit(f_handle, p0, x_data, y_data, lb, ub, opts);
  ```
- **Result Mapping:** Converts MATLAB double arrays, exit flags, and covariance matrices into the standard SciModel `FitResult` domain object.

### 4.3 LLM Formulation Adapter (`LLMRecommender`)
- Operates via structured system prompts with strict JSON Schema output.
- Ingests:
  - Column summaries (min, max, mean, variance).
  - Detected data features (monotonicity, sign changes, saturation indicators).
  - User research objective (e.g. "Identify substrate affinity and inhibition threshold").
- Validates the returned candidate expression using `ModelFormula` AST parser. Rejects any response containing unsupported syntax or undefined symbols.

---

## 5. Security & Isolation Guardrails

| Risk | Mitigation |
|---|---|
| **Arbitrary Code Execution in Python** | AST parser allows only whitelist of arithmetic functions. No `eval()`, `exec()`, or `import`. |
| **Command Injection in MATLAB** | Use parameterized function handles `@(p, x)` rather than constructing raw `matlab.eval()` strings with user text. |
| **Missing MATLAB Runtime/License** | Explicit runtime detection; test suite skips MATLAB tests gracefully (`pytest.mark.skipif(not matlab_available)`). |
| **LLM Hallucinations** | Formulas must be verified against physical units, parameter bounds, and must undergo numerical goodness-of-fit testing before presentation. |

---

## 6. CLI Command Surface

```bash
# 1. Ask LLM to propose candidate models based on inspected data
scimodel formula recommend examples/enzyme_kinetics_puromycin.csv \
    --objective "catalytic efficiency and affinity" \
    --out candidates.json

# 2. Fit a specific formula using the default SciPy backend
scimodel formula fit examples/enzyme_kinetics_puromycin.csv \
    --formula "(Vmax * s) / (Km + s)" \
    --params "Vmax:0:inf,Km:0:inf" \
    --backend scipy

# 3. Fit the same formula using the MATLAB engine (if installed)
scimodel formula fit examples/enzyme_kinetics_puromycin.csv \
    --formula "(Vmax * s) / (Km + s)" \
    --params "Vmax:0:inf,Km:0:inf" \
    --backend matlab

# 4. Generate validation and comparison report
scimodel report build examples/enzyme_kinetics_puromycin.csv \
    --output-dir outputs/matlab_comparison
```

---

## 7. Phased Implementation Plan

1. **Phase Next.1: Formula Domain & AST Safe Evaluator**
   - Create `src/scimodel/domain/formula.py` with `ParameterSpec`, `ModelFormula`, and AST evaluator.
   - Add unit tests verifying safe evaluation and syntax rejection.

2. **Phase Next.2: Generic SciPy Formula Solver**
   - Create `src/scimodel/adapters/scipy_formula_solver.py`.
   - Verify parity with current Michaelis-Menten solver.

3. **Phase Next.3: MATLAB Engine Adapter**
   - Create `src/scimodel/adapters/matlab_solver.py`.
   - Add graceful fallback and environment detection.
   - Add integration tests skipped when MATLAB is absent.

4. **Phase Next.4: LLM Formulation Port & Provider**
   - Define `FormulaRecommenderPort`.
   - Implement structured LLM prompting and schema validation.

5. **Phase Next.5: CLI Integration & Comparative Reporting**
   - Wire `formula recommend` and `formula fit` into `scimodel.interfaces.cli`.
   - Update reports to include model formula, backend metadata, and comparison tables.
