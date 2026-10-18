# SciModel Private Pilot Report

**Date:** 2026-10-18  
**Environment:** Python 3.14.8 in `.venv`  
**Scope:** Full CLI workflow on both approved Phase 0 datasets

## Executive result

The functional private pilot passed. Both approved datasets were inspected, validated, fitted, and reported successfully using the documented non-interactive CLI. Scientific accuracy and reproducibility checks passed.

The resource gate is not fully passed: the measured child-process peak RSS was approximately 105 MB, above the original 20 MB planning target. This measurement includes the Python interpreter and NumPy/SciPy runtime, so it is not equivalent to model-array memory alone. It remains a performance issue to investigate before making a strict memory claim.

## Results

| Dataset | Rows | Inspect | Validate | R² | Vmax | Report artifacts | Result |
|---|---:|---|---|---:|---:|---|---|
| Puromycin | 12 | Pass | Pass | 0.961261 | 212.683726 | 4/4 | Functional pass |
| Synthetic | 14 | Pass | Pass | 0.999351 | 199.980972 | 4/4 | Functional pass |

## CLI timing

Measured in fresh subprocesses using the repository `.venv`:

| Dataset | Inspect | Validate | Report build |
|---|---:|---:|---:|
| Puromycin | 0.5427 s | 0.5525 s | 0.6417 s |
| Synthetic | 0.5579 s | 0.5667 s | 0.5806 s |

The original `<100 ms` target was a planning target, not a demonstrated requirement. The current end-to-end process is under one second for these small datasets but does not meet the strict 100 ms target.

## Checks

| Check | Result | Evidence |
|---|---|---|
| Data inspection | Pass | Both datasets returned valid profiles |
| Scientific fit | Pass | Known-answer tests and reference values pass |
| Validation | Pass | All required validation checks passed |
| Report generation | Pass | Markdown, fit JSON, validation JSON, and manifest JSON generated for each dataset |
| Reproducibility metadata | Pass | SHA-256, configuration, software, Python, and platform recorded |
| Local-only behavior | Pass | Pilot artifact scan found no network/upload markers |
| Runtime target | Review required | 0.54–0.64 s per command exceeds the 100 ms planning target |
| Memory target | Review required | Peak child-process RSS approximately 105 MB exceeds the 20 MB planning target |

## Pilot decision

**Decision: Automated private pilot complete; external human review remains required.**

The workflow is suitable for private evaluation. ADR 004 records that the original 100 ms / 20 MB values are historical planning targets, not achieved release claims. The project must continue to report the measured cold-start runtime and process RSS until a reproducible benchmark methodology and any hard target are defined.

## Follow-up issues

1. Measure memory with a documented methodology that separates interpreter/library startup from dataset/model allocations.
2. Profile startup and command runtime before optimizing.
3. Repeat the pilot with at least one domain-qualified human reviewer following the quick start without assistance.
