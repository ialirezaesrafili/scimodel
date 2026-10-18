# Reference Examples & Datasets

This directory contains redistributable and synthetic datasets used for testing, validation, and benchmarking of SciModel workflows.

## 1. Puromycin Enzyme Kinetics (`enzyme_kinetics_puromycin.csv`)

- **Domain:** Biochemical Reaction Kinetics / Enzyme Catalysis
- **Origin/Provenance:** Experimental data published by Treloar (1974), popularized by Bates & Watts (1988) in *Nonlinear Regression Analysis and Its Applications*, Table 3.1. Widely distributed in the public domain (e.g., standard R `datasets::Puromycin`).
- **Permission to use:** Public domain benchmark dataset.
- **Observations:** 12 experimental rows (treated enzyme system, 6 concentrations in duplicate).
- **Variables & Units:**
  - `substrate_conc`: Substrate concentration $[S]$ in parts per million ($\text{ppm}$).
  - `reaction_velocity`: Initial reaction velocity $v$ in counts per minute squared ($\text{counts}/\text{min}^2$).
- **Expected Behavior / Reference Fit:**
  - Model: Michaelis-Menten $v = \frac{V_{\max} [S]}{K_m + [S]}$
  - Reference parameters (Bates & Watts):
    - $V_{\max} = 212.684 \pm 6.947\ \text{counts}/\text{min}^2$
    - $K_m = 0.06412 \pm 0.00828\ \text{ppm}$
    - Residual Sum of Squares (RSS): $\approx 1195.45$

## 2. Synthetic Enzyme Kinetics (`enzyme_kinetics_synthetic.csv`)

- **Domain:** Biochemical Reaction Kinetics / Controlled In Silico Assay
- **Origin/Provenance:** Generated deterministically for SciModel known-answer testing with known parameter ground truth and simulated measurement error.
- **Permission to use:** Project synthetic fixture (Apache 2.0).
- **Observations:** 14 rows (7 distinct concentrations with duplicate measurements).
- **Variables & Units:**
  - `substrate_conc`: Substrate concentration $[S]$ in millimolar ($\text{mM}$).
  - `reaction_velocity`: Initial reaction velocity $v$ in $\mu\text{mol} / (\text{L} \cdot \text{min})$.
- **Ground Truth Parameters:**
  - $V_{\max} = 200.0\ \mu\text{mol} / (\text{L} \cdot \text{min})$
  - $K_m = 0.05\ \text{mM}$
- **Expected Numerical Recovery:**
  - Fitted $V_{\max} \in [195.0, 205.0]$
  - Fitted $K_m \in [0.045, 0.055]$
  - $R^2 > 0.99$

## 3. Advanced Replicate Enzyme Kinetics (`enzyme_kinetics_advanced.csv`)

- **Domain:** Biochemical Reaction Kinetics / Controlled In Silico Assay
- **Origin/Provenance:** Synthetic robustness fixture with nonuniform substrate spacing,
  replicate measurements, realistic noise, and an extra metadata column.
- **Permission to use:** Project synthetic fixture (Apache 2.0).
- **Observations:** 20 rows across 10 distinct concentrations, with two replicates each.
- **Variables:** `substrate_conc`, `reaction_velocity`, and non-model metadata `replicate`.
- **Expected Behavior:** The workflow should accept the extra column and repeated
  concentration levels, converge on a positive fit, and preserve uncertainty and
  limitations in the generated report.

## 4. Non-Kinetics Negative Control (`non_kinetics_exponential_decay.csv`)

- **Domain:** Exponential decay, intentionally outside the current kinetics scope.
- **Purpose:** Test whether the assistant reports a poor Michaelis–Menten fit honestly
  when custom columns are supplied.
- **Variables:** `time` and `concentration`.
- **Expected Behavior:** Data inspection should pass structurally, but the current
  Michaelis–Menten validation should fail or recommend investigation because the
  response decreases rather than follows the supported increasing saturation model.
