# Development

## Toolchain

Python ≥ 3.11 (CI: 3.11–3.14), Go ≥ 1.22, Bash. `shellcheck` is optional locally and used
in CI.

```bash
scripts/setup.sh          # .venv with SciModel editable + dev + all extras, Go binary in bin/
source .venv/bin/activate
```

## Workflow scripts

All scripts are in `scripts/`, share `lib.sh` (strict mode, logging, venv detection), and
behave the same locally and in CI.

| Script | Does |
|---|---|
| `setup.sh [--no-go]` | Create the environment and build the batch runner |
| `check.sh [all\|python\|go\|shell]` | Quality gate: ruff format/lint, strict mypy, pytest with ≥ 85% coverage; gofmt, go vet, `go test -race`; bash syntax + shellcheck |
| `coverage.sh` | Python HTML/XML and Go coverage reports in `coverage/` |
| `build.sh [--go-only] [--cross]` | Wheel + sdist in `dist/`; `bin/scimodel-batch`; with `--cross`, binaries for linux/darwin/windows × amd64/arm64 |
| `smoke.sh` | Regenerate examples, run `discover` on each, assert convergence and grade |
| `batch.sh <folder> [flags]` | Build (if needed) and run the Go batch runner with the venv's `scimodel` |
| `release.sh [--tag]` | Check versions and changelog, require a clean tree, run the full gate, build, `twine check`, and optionally tag |

## Tests

```text
tests/unit/          components in isolation (reader, profiling, engines, quality, ranking,
                     LLM providers with fake clients, config, formula, solvers, CLI parser)
tests/integration/   CLI commands, scripted interactive sessions, report bundles,
                     original kinetics/assistant workflows
tests/scientific/    known-answer benchmarks against certified or generated ground truth
batch/**/_test.go    worker pool limits, ordering, timeouts, cancellation, scanning,
                     fingerprints, summaries, incremental reuse, CLI exit codes
```

Rules:

- Numerical behaviour needs a **known-answer test**: a certified reference (e.g. Bates &
  Watts Puromycin values) or synthetic data with documented ground truth
  (`examples/generate_examples.py`).
- No test may need a network or a language model. Providers are tested with fake clients.
- Discovery tests use small time budgets and explicit engine lists to stay fast.

Current results (`scripts/coverage.sh`):

| Suite | Result |
|---|---|
| Python | 145 tests passing, **89.27%** line+branch coverage (gate: 85%) |
| Go | all packages passing under `-race`; **80.6%** total (cmd 75.0%, runner 71.4%, summary 93.4%, workspace 80.0%) |

## Adding things

See [Architecture → Extension points](architecture.md#extension-points). Record decisions
that change public interfaces, scientific behaviour, dependencies or data handling as an
ADR in `docs/decisions/`.

## Releasing

1. Update `version` in `pyproject.toml` and `src/scimodel/__init__.py`, and add a
   `## [x.y.z]` section to `CHANGELOG.md`.
2. `scripts/release.sh` (dry run), then `scripts/release.sh --tag`.
3. `git push origin vX.Y.Z`. `.github/workflows/release.yml` re-runs the gate, builds the
   wheel, sdist and Go binaries, creates the GitHub release (pre-release for `rc`/`b` tags),
   and publishes to PyPI through trusted publishing (configure the `pypi` environment
   once).

Before the first public release, replace `REPLACE_WITH_OWNER` in `pyproject.toml`,
`CITATION.cff`, `.github/CODEOWNERS` and `README.md`. Also confirm that no private data is
in the history, and that the dataset licences in `examples/README.md` still hold.
