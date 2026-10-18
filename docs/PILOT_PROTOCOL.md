# SciModel Private Pilot Protocol

## Purpose

The private pilot evaluates the complete documented workflow before public release. It checks scientific behavior, reproducibility, usability of the non-interactive CLI, privacy boundaries, and resource behavior.

## Pilot procedure

Run the following for each approved dataset using the project virtual environment:

```bash
source .venv/bin/activate
python -m scimodel data inspect DATA.csv
python -m scimodel model validate DATA.csv
python -m scimodel report build DATA.csv --output-dir reports/pilot-run
```

Record:

- Exit status for every command.
- Dataset row count and validation status.
- Fitted parameters and accuracy against the reference criteria.
- Report and manifest artifact presence.
- Runtime and peak memory measured from a fresh process.
- Any network/upload behavior.
- Installation or interpretation problems.

## Pass criteria

- All commands complete with exit code `0` for approved datasets.
- Validation checks pass and known-answer accuracy remains within Phase 0 tolerances.
- All four report artifacts are generated and readable.
- The manifest identifies the exact input file and configuration.
- No data is sent to external services.
- Resource behavior is reviewed against the 100 ms / 20 MB planning targets, with any environment overhead clearly distinguished from application behavior.

The pilot is not a public-release approval. Any scientific correctness, data-integrity, privacy, or reproducibility failure blocks release.
