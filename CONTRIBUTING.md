# Contributing to SciModel

SciModel is intended to support careful, reproducible scientific work. Contributions that affect scientific calculations must include tests, explain assumptions, and document limitations.

## Before contributing

1. Read the [roadmap](docs/SciModel_End_to_End_Project_Roadmap.md) and [architecture guide](docs/ARCHITECTURE.md).
2. Check existing issues and record significant design decisions as an ADR.
3. Never commit private laboratory data, credentials, or material without redistribution permission.

## Development expectations

- Keep domain logic independent from the CLI, filesystems, and third-party libraries.
- Prefer small, explicit interfaces over hidden global state.
- Add known-answer tests for numerical behavior.
- Keep transformations and configuration visible in generated reports.
- Run formatting, linting, type checking, and tests before opening a pull request.
