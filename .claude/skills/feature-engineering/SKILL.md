---
name: feature-engineering
description: Turns raw experimental measurements into meaningful, physically interpretable predictors for SciModel workflows — derived quantities, unit-consistent transforms, replicate aggregation, and leakage-safe preprocessing. Use when preparing predictors for a model fit, comparing candidate transforms, or reviewing whether a transform distorts errors.
---

# Feature engineering for scientific data

SciModel's rule: **inspection never changes data; every transform is explicit, reviewable and recorded.** Feature engineering happens after `data inspect`, never inside it.

## Principles

1. **Physics first.** Prefer features with a physical meaning (rates, ratios, dimensionless groups, log-concentrations) over opaque combinations. Name each feature after what it measures, with units.
2. **Keep raw values.** Never overwrite source columns. Derived columns get new names (`log10_substrate_conc`, `velocity_per_enzyme`).
3. **Watch the error model.** A transform changes the noise structure. Example: Lineweaver–Burk (`1/v` vs `1/[S]`) inflates noise at low `[S]`; SciModel therefore uses it only for initial guesses, never for the reported fit. State the error consequence of every transform.
4. **No leakage.** Fit scalers, imputers and encoders on training folds only (use `sklearn.pipeline.Pipeline`). Group replicate measurements so that replicates of one condition never sit in both train and test (`GroupKFold`).
5. **Record everything.** Each transform goes into the run configuration/manifest: name, formula, input columns, parameters, and the reason.

## Common scientific features

| Situation | Feature | Note |
|---|---|---|
| Wide concentration range | `log10(x)` | Requires `x > 0`; report how zeros are handled — never drop them silently |
| Replicates | per-level mean, SD, n | Keep the raw replicates for fitting; use aggregates for diagnostics and weights |
| Heteroscedastic noise | weights `1/SD²` per level | Prefer weighting over transforming the response |
| Different scales | dimensionless ratios (e.g. `[S]/Km_guess`) | Make sure the reference value is not itself fitted on test data |
| Time series | lags, rolling means, time since start | Respect time order; never shuffle |
| Batches/plates | batch identifier as group | Use for grouped CV or random effects, not as a free predictor |

## Workflow

1. Run `python -m scimodel data inspect <file>` and read the warnings.
2. Write down candidate features and the physical justification for each.
3. Implement transforms as pure functions (domain or application layer, no I/O), unit-tested with small hand-computed cases.
4. Check the effect: residual plots and diagnostics with and without the feature, using the same validation split.
5. Keep a feature only if it improves out-of-sample performance or interpretability **and** has a physical rationale.

## Guardrails

- Never impute, drop outliers, or rescale units without an explicit user option and a manifest entry.
- Never select features using the full dataset and then report cross-validated scores on that same dataset.
- When the dataset is small (fewer than ~30 observations, like the kinetics examples), prefer zero or one engineered feature with a mechanistic rationale over automatic feature search.

See also: `scikit-learn` (pipelines, CV), `statistical-analysis`, `uncertainty-and-units`.
