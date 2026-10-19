---
name: symbolic-regression
description: Searches for interpretable closed-form equations that describe experimental data (PySR, SymPy candidate libraries, SINDy for dynamics) and validates them against mechanistic models. Use when the user wants equation discovery, wants to check whether a simpler or different functional form fits better, or asks for an interpretable alternative to a black-box model.
---

# Symbolic regression and equation discovery

Equation discovery is a **hypothesis generator, not a verdict.** A discovered formula is only useful if it is simpler, generalizes out of sample, and makes physical sense. SciModel must never present a discovered equation as the true mechanism.

## Tool choice

| Need | Tool | Install |
|---|---|---|
| General expression search, Pareto front of accuracy vs. complexity | **PySR** | `uv pip install pysr` (first run installs a Julia backend; needs network once) |
| Small, curated library of candidate forms (recommended first) | **SymPy** + `scipy.optimize.least_squares` | already available |
| Governing ODEs from time series | **PySINDy** | `uv pip install pysindy` |

Start with the curated-library approach. Use PySR only when the candidate library cannot explain the data.

## Curated candidate library (enzyme-kinetics example)

```python
import sympy as sp
S, Vmax, Km, n, Ki = sp.symbols("S Vmax Km n Ki", positive=True)
candidates = {
    "michaelis_menten": Vmax * S / (Km + S),
    "hill": Vmax * S**n / (Km**n + S**n),
    "substrate_inhibition": Vmax * S / (Km + S + S**2 / Ki),
}
# lambdify each, fit with bounded least_squares, compare with AICc/BIC
```

Fit each candidate with the same solver settings and the same data, then compare with **AICc** (small samples) or BIC, and report parameter standard errors. Declare "not distinguishable" when ΔAICc < 2.

## PySR usage pattern

```python
from pysr import PySRRegressor
model = PySRRegressor(
    niterations=200,
    binary_operators=["+", "-", "*", "/"],
    unary_operators=["exp", "log"],
    maxsize=20,
    model_selection="best",
    random_state=0, deterministic=True, parallelism="serial",  # reproducible
)
model.fit(X, y)
print(model.equations_)  # Pareto front: complexity vs. loss
```

## Validation checklist (required before reporting a discovered equation)

1. **Holdout:** evaluate on data not used in the search (grouped by experimental condition).
2. **Dimensional check:** units must be consistent (see `uncertainty-and-units`).
3. **Physical limits:** correct sign, monotonicity, asymptotes and behaviour at zero.
4. **Parameter refit:** refit the discovered form with bounded least squares to get standard errors.
5. **Compare with the mechanistic baseline** with an information criterion; report both.
6. **Reproducibility:** record the seed, operator set, maxsize, iterations and library versions in the manifest.

## Guardrails

- With fewer than ~20 points, symbolic search will overfit; restrict to the curated library.
- Never run untrusted generated code; evaluate expressions through SymPy `lambdify`, never `eval`.
- Report the discovered equation as "empirical candidate", alongside its limitations.

See also: `sympy`, `statistical-analysis`, `parameter-optimization`.
