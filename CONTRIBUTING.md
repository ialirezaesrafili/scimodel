# Contributing to SciModel

SciModel supports careful, reproducible scientific work. Contributions that affect
scientific results must include known-answer tests and must document their assumptions
and limitations.

## Getting set up

```bash
scripts/setup.sh        # Python venv + Go batch runner
scripts/check.sh        # the same gate CI runs
```

Read [Architecture](docs/architecture.md) and [How it works](docs/how-it-works.md) first.

## Expectations

- Keep `domain/` free of I/O, CLI, SciPy, and network code. Reach technology through ports.
- Add a known-answer test for numerical behaviour (certified reference or generated ground
  truth in `examples/generate_examples.py`).
- Tests must not need a network or a language model; use fake clients.
- Record long-lived decisions as an ADR in `docs/decisions/`.
- Update `CHANGELOG.md` under an `Unreleased` heading.
- Never commit private laboratory data, credentials, or material without redistribution
  permission.
