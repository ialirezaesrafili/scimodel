# ADR 004: Private-pilot resource targets are measured, not release claims

- **Status:** Accepted
- **Date:** 2026-10-18
- **Deciders:** SciModel Architecture & Scientific Working Group

## Context

The original Phase 0 planning targets were less than 100 ms runtime and less than 20 MB peak memory. The automated pilot measured 0.54–0.64 seconds per cold CLI process and approximately 105 MB child-process RSS on Python 3.14 with NumPy/SciPy.

The measurement includes interpreter and scientific-library startup, not only model arrays. The current datasets are small, and the workflow completes reliably. Treating the original numbers as a hard release gate without a defined hardware and measurement methodology would create a misleading claim.

## Decision

For the current private prototype, resource measurements are reported as evidence, not as a release claim. The pilot acceptance criteria are:

- Every approved dataset completes the documented workflow successfully.
- Cold CLI execution remains below one second on the reference environment.
- Memory methodology distinguishes process/runtime overhead from dataset and model allocations before setting a hard limit.
- Any future hard performance target must identify hardware, Python/dependency versions, warm/cold state, command, and measurement tool.

The original 100 ms / 20 MB values remain historical planning targets and are not marked as achieved.

## Consequences

- The project does not claim to meet the original resource targets.
- Performance optimization is evidence-driven and deferred until profiling identifies a user-relevant bottleneck.
- A future release may define stricter targets with a reproducible benchmark protocol.
