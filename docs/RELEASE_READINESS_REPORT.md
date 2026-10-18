# SciModel Release Readiness Report

**Review date:** 2026-10-18  
**Release candidate:** `0.1.0.dev0`  
**Decision:** Not yet approved for public release

## Verified

- 32 automated tests pass.
- Measured coverage is 89%, above the configured 85% threshold.
- Ruff linting and formatting pass.
- The production wheel builds successfully with Hatchling.
- The built wheel installs into a clean target directory and runs `--version` and the synthetic validation workflow.
- Both approved datasets pass the automated private pilot.
- License, citation, contribution, security, conduct, issue, and pull-request metadata are present.
- Source-distribution configuration includes source, tests, documentation, examples, license, citation, and governance files.

## Open release blockers

| Blocker | Owner/action | Status |
|---|---|---|
| Human scientific review | A domain-qualified reviewer must follow the quick start and review outputs | Open |
| Repository identity placeholders | Replace `REPLACE_WITH_OWNER` in URLs, CODEOWNERS, security links, and citation metadata | Open |
| Legal/provenance review | Confirm Apache-2.0 ownership and all dependency/dataset permissions | Open |
| Security contact | Configure a real private vulnerability-reporting path | Open |
| Mypy verification | Strict mypy passes locally; verify again in the release matrix | Review |
| Version/release approval | Choose a public version and approve release notes | Open |

## Packaging note

The production wheel path is verified. Editable installation additionally needs Hatchling’s `editables` helper, which is a development-environment concern and does not block wheel creation or installation.

## Release decision

Keep the repository private until every open blocker is resolved and the project owner explicitly approves publication. The software is technically demonstrable, but public release requires human scientific, legal, security, and ownership review.
