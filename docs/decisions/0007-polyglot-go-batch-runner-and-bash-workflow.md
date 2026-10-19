# ADR 007: Go for concurrent batch execution, Bash for workflow automation

- **Status:** Accepted
- **Date:** 2026-10-19

## Context

Labs hold many datasets across folders. Analyzing them one by one is slow. Python
multiprocessing inside the CLI would complicate the scientific core and its tests.
Developer tasks were documented as prose commands rather than executable scripts.

## Decision

- Add `batch/`, a dependency-free Go module producing a static `scimodel-batch` binary. It
  scans, fingerprints (SHA-256, parallel), and runs `scimodel discover --json` in a bounded
  worker pool with per-job timeouts, signal-driven cancellation, and incremental reruns.
  It aggregates results into `batch_summary.{json,md}`.
- The Go code never performs scientific computation. The Python CLI's JSON output is the
  contract between them.
- Add `scripts/*.sh` (strict-mode Bash sharing `lib.sh`) for setup, checks, coverage,
  builds, smoke tests, batch runs and releases. CI calls the same scripts.

## Alternatives considered

- **Python `concurrent.futures`:** workable, but process management, cancellation and
  timeouts are clumsier, and it ships no standalone binary.
- **Makefile:** less portable error handling and logic. Bash scripts are explicit and
  testable with `bash -n`/shellcheck.

## Consequences

- Contributors may need Go to work on `batch/`. Python-only work is unaffected, and CI
  runs separate Python, Go and shell jobs.
- The `discover --json` schema is now a public contract. Breaking it requires a version
  bump and a matching update in `batch/internal/summary`.
