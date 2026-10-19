---
name: scimodel-testing
description: Automated testing workflow for the SciModel repository — where tests go (unit, integration, scientific), known-answer and tolerance rules, the commands CI runs (ruff, mypy, pytest with an 85% coverage gate), and how to add regression tests so changes never break existing scientific behaviour. Use whenever changing code in this repo, adding a model or check, or fixing a bug.
---

# SciModel automated testing

Every change that touches scientific behaviour must come with tests, and the existing known-answer tests must keep passing unchanged. Never loosen a tolerance to make a test pass without a documented reason (an ADR or changelog entry).

## Test layout

| Directory | What belongs there |
|---|---|
| `tests/unit/` | Pure functions, CLI argument parsing, small contracts; no file I/O beyond `tmp_path` |
| `tests/integration/` | CSV reading, CLI end-to-end runs (`python -m scimodel ...`), report artifacts, exit codes |
| `tests/scientific/` | Known-answer fits, synthetic recovery, tolerances from `docs/PHASE_0_SCOPE_BRIEF.md` |

## Commands (same as CI, `.github/workflows/ci.yml`)

```bash
ruff format --check .
ruff check .
mypy
pytest --cov=scimodel --cov-report=term-missing --cov-fail-under=85
```

Run all four before committing. If a tool is missing: `pip install -e ".[dev]"`.

## Rules for new tests

1. **Known answers:** compare with certified or independently computed values (e.g. Puromycin Vmax 212.684, Km 0.06412, RSS 1195.45) using `pytest.approx` with the tolerance declared in the scope brief.
2. **Synthetic truth:** fixed seeds; assert recovery within the declared CI or relative tolerance.
3. **Failure paths:** every `ModelFitError`/validation failure has a test that checks the message and, for the CLI, the exit code.
4. **Unsupported cases:** each case in the scope brief (negative values, < 4 levels, substrate inhibition, cooperativity, `[S]max < 0.5·Km`) needs a dataset that triggers it and a test proving the tool warns or refuses.
5. **Regression first for bugs:** write the failing test, then fix.
6. **Determinism:** no network, no wall-clock dependence, no unseeded randomness. Use `tmp_path` for outputs.
7. **Report contracts:** when the JSON or Markdown output changes, update the integration tests and `docs/CLI_REFERENCE.md` together.

## Before pushing

- All four commands pass locally.
- Updated test counts or coverage figures in docs only when they actually changed (`docs/PROJECT_STATUS_REPORT.md`).
- `CHANGELOG.md` entry for user-visible behaviour changes.

See also: `robustness-testing` (noise sweeps, Hypothesis), `parameter-optimization` (solver test requirements).
