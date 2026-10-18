# SciModel Release Checklist

Use this checklist before changing repository visibility or publishing a release. A public repository is not automatically a release-ready scientific product.

## Scientific readiness

- [x] Phase 0 scope and reference datasets approved.
- [x] Known-answer solver tests pass.
- [x] Validation checks, uncertainty, limitations, and reports are implemented.
- [x] Automated private pilot passes both approved datasets.
- [ ] Domain-qualified human pilot review completed.
- [ ] Open pilot issues classified and critical issues closed.

## Engineering readiness

- [x] `pyproject.toml` and `src/` package layout are present.
- [x] CLI reference and quick start are documented.
- [x] CI runs linting, formatting, type checking, tests, and coverage.
- [x] Coverage is 85.63%, above the configured 85% minimum.
- [x] Production wheel builds successfully and installs into a clean target directory.
- [ ] Clean install from a built artifact verified across all supported Python versions.
- [ ] Mypy passes in the release environment.
- [ ] Final dependency versions and compatibility policy reviewed.

## Legal, security, and provenance

- [x] Apache-2.0 license is present.
- [x] Security, contribution, and conduct policies are present.
- [x] Example data provenance and permissions are documented.
- [x] Citation metadata is present.
- [ ] Actual repository owner replaces all `REPLACE_WITH_OWNER` placeholders.
- [ ] Maintainer reviews license, dependency, dataset, and third-party-material permissions.
- [ ] Repository history is scanned for secrets and private data.
- [ ] Security contact and advisory process are configured.

## Release operation

- [ ] Version is selected and release notes are complete.
- [ ] Changelog is updated.
- [ ] Clean artifact installs and runs the quick start.
- [ ] Release contents are reviewed on a clean machine/environment.
- [ ] Tag and publication are approved by the project owner.

## Current decision

The project is **not yet approved for public release**. Automated scientific and engineering gates pass, but human scientific review, clean artifact installation, owner identity, and final legal/security review remain required.
