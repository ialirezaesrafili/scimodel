# Claude Code project skills

Claude Code loads every `*/SKILL.md` in this directory automatically for anyone working in this repository, locally or in cloud sessions.

## Capability map

| Capability | Skills |
|---|---|
| Feature engineering | `feature-engineering`, `scikit-learn` |
| Bayesian modeling | `pymc` |
| Symbolic regression | `symbolic-regression`, `sympy` |
| Sensitivity analysis | `sensitivity-analysis` |
| Optimization | `parameter-optimization`, `pymoo` |
| Explainable AI (SHAP) | `shap` |
| Time-series modeling | `statsmodels`, `aeon` |
| Physics-informed ML | `physics-informed-ml` |
| Robustness testing | `robustness-testing` |
| Automated testing | `scimodel-testing` |
| Supporting | `statistical-analysis`, `uncertainty-and-units` |

## Sources

- **Written for SciModel:** `feature-engineering`, `symbolic-regression`, `sensitivity-analysis`, `parameter-optimization`, `physics-informed-ml`, `robustness-testing`, `scimodel-testing`.
- **Vendored unchanged from [K-Dense-AI/scientific-agent-skills](https://github.com/K-Dense-AI/scientific-agent-skills)** (commit `593377b`, collection under the MIT license in `K-DENSE-LICENSE.md`; each `SKILL.md` states its own license): `scikit-learn`, `pymc`, `sympy`, `pymoo`, `shap`, `statsmodels`, `aeon`, `statistical-analysis`, `uncertainty-and-units`.

To update a vendored skill, copy the folder again from a newer upstream commit and update the commit hash above.

Skills describe workflows only; their Python dependencies (PyMC, SHAP, SALib, PySR, …) are **not** SciModel dependencies and must stay optional. The `.claude/` directory is excluded from Ruff in `pyproject.toml` because it contains third-party helper scripts.
