# ADR 003: SciPy is the default backend; MATLAB is deferred

- **Status:** Accepted
- **Date:** 2026-10-18
- **Deciders:** SciModel Architecture & Scientific Working Group

## Context

The Phase 5 roadmap requires a backend decision. The current workflow is fully supported by open-source Python and SciPy. No selected Phase 0 or Phase 3 requirement needs a MATLAB-only algorithm, toolbox, or numerical result.

MATLAB would add installation, licensing, environment-detection, compatibility, and reproducibility requirements for users who may not have a licensed MATLAB installation.

## Decision

SciPy remains the default and only required numerical backend for the MVP. MATLAB integration is deferred until a concrete, documented scientific capability cannot be provided reliably by the supported open-source backend.

If MATLAB is later added, it must be an optional adapter with explicit environment checks, licensing/setup documentation, skipped integration tests when unavailable, and no change to the default workflow.

## Consequences

- The default installation remains open-source and reproducible without MATLAB.
- The current CLI and reports do not depend on proprietary software.
- A future MATLAB adapter must implement the same application/solver contract and pass equivalent known-answer tests.
