# ADR 002: CSV-first data input for Phase 2

- **Status:** Accepted
- **Date:** 2026-10-17
- **Deciders:** SciModel Architecture & Scientific Working Group

## Context

The MVP roadmap mentions CSV and Excel intake, while the selected Phase 0 reference workflow uses small tabular CSV datasets. Phase 2 needs a deterministic, dependency-light input path before model implementation begins.

## Decision

Implement CSV input as the supported Phase 2 format. The reader will preserve source values, reject malformed structure, and produce structured profiling and validation results. Excel support is deferred until a real user workflow or dataset requires it.

Excel support may be added later as an adapter behind the same application contract. It must remain optional so the default installation does not require spreadsheet-specific dependencies.

## Consequences

- The Phase 2 exit gate applies to CSV inputs and the approved kinetics datasets.
- CSV behavior can be tested in a clean environment without a proprietary or spreadsheet runtime.
- Adding Excel later must not change domain validation or CLI result contracts.
- The roadmap and status report must keep the deferred Excel decision visible.
