---
name: robustness-testing
description: Checks how SciModel fits and validations behave under measurement noise, outliers, missing replicates, distribution shift, and edge-case inputs — noise-injection sweeps, bootstrap and jackknife stability, adversarial datasets for unsupported cases, and property-based tests with Hypothesis. Use when hardening a model or validator, before a release, or when a user asks how reliable a result is.
---

# Robustness testing

Goal: show that results degrade **gracefully and visibly** — good data gives stable estimates; bad or unsupported data gives a clear warning or refusal, never a confident wrong answer.

## 1. Statistical stability (per fit)

- **Bootstrap** (resample residuals or, with replicates, resample within concentration levels) → distribution of each parameter; compare with covariance-based CIs.
- **Jackknife / leave-one-out** → flag observations whose removal changes a parameter by more than its standard error (influential points).
- **Multi-start** → the optimum must not depend on the initial guess.

## 2. Noise and shift sweeps (synthetic, fixed seeds)

Generate data from a known truth, then vary one factor at a time:

| Factor | Example sweep | Expected behaviour |
|---|---|---|
| Noise level | CV 1% → 30% | CIs widen; coverage of the truth stays ~95% |
| Outliers | 1–2 points ×3 | robust-loss fit stays close; standard fit flags large residuals |
| Design range | `[S]max` from 5·Km down to 0.2·Km | below 0.5·Km the tool must refuse or warn (unidentifiable) |
| Model mismatch | data from Hill (n=2) or substrate inhibition | residual-runs / model-comparison check must flag it |
| Sample size | 4 → 30 points | fewer than 4 levels must be rejected |

Assert **coverage** (fraction of runs where the 95% CI contains the truth) within a tolerance band (e.g. 0.90–0.99 over 200 seeds), not exact values.

## 3. Input edge cases

Empty file, header only, NaN/inf, negative values, duplicates, a single concentration level, huge values (1e300), tiny values (1e-300), non-UTF-8 encoding, very wide or very long files. Each should give a defined exit code and message (see `docs/CLI_REFERENCE.md`).

## 4. Property-based tests (Hypothesis)

```python
from hypothesis import given, settings, strategies as st

@settings(max_examples=200, deadline=None)
@given(vmax=st.floats(10, 1e3), km=st.floats(1e-3, 10))
def test_noise_free_recovery(vmax, km):
    s = km * np.array([0.1, 0.3, 1, 3, 10])
    fit = fit_michaelis_menten(s, michaelis_menten(s, vmax, km))
    assert fit.parameters["vmax"] == pytest.approx(vmax, rel=1e-4)
    assert fit.parameters["km"] == pytest.approx(km, rel=1e-4)
```

Useful properties: exact recovery from noise-free data, invariance to row order, scale equivariance (multiplying `v` by c multiplies `Vmax` by c), validator never returns `valid=True` for data from an unsupported regime.

## Organisation in this repo

- Fast deterministic cases → `tests/scientific/` and `tests/integration/`.
- Long sweeps (hundreds of seeds) → mark with `@pytest.mark.slow` and run them in a separate CI job or before releases.
- Record sweep settings and seeds so failures can be reproduced exactly.

See also: `scimodel-testing`, `statistical-analysis`, `sensitivity-analysis`.
