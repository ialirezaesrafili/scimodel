# ADR 006: General equation discovery and evidence-based model selection

- **Status:** Accepted
- **Date:** 2026-10-19
- **Supersedes:** the single-domain scope of ADR 001 (the kinetics workflow is retained)

## Context

SciModel accepted only enzyme-kinetics CSV files with fixed column names and fitted one
model. Researchers need to bring any tabular experimental data, find candidate laws, and
understand how far to trust them, without a hosted service and without trusting an LLM's
numbers.

## Decision

1. Add a domain-neutral `Dataset` and a multi-format reader. Formulas accept any number of
   variables.
2. Generate candidates from independent engines (model library, sparse regression,
   symbolic regression, optional LLM, user formulas). All candidates share one fitting,
   cross-validation, ranking and quality pipeline.
3. Rank by **AICc + 2·ln M**, where M is the size of each engine's structure search. Apply a
   parsimony guard (parameters with |estimate| < SE) and, within ΔAICc < 2, prefer
   mechanistic → curated → data-mined → simpler.
4. Grade the top candidates with model-agnostic checks. A NumPy neural network acts as a
   learnable-signal ceiling.
5. Keep language models advisory: profile-only context by default, AST-validated
   proposals, locally computed numbers, labelled narratives.

## Alternatives considered

- **Plain AICc ranking:** symbolic regression won on Puromycin by searching thousands of
  shapes (selection bias). Rejected.
- **Cross-validation alone:** on n = 8 (Kepler), leave-one-out also preferred overfitted
  terms. CV is reported, but it does not replace an information criterion.
- **PyTorch for the neural ceiling:** a heavy dependency for a diagnostic that a small
  NumPy MLP provides. Can be added later behind an adapter.
- **PySR/Julia for symbolic regression:** stronger search, but a large runtime
  dependency. The engine interface allows adding it as an optional adapter.

## Consequences

- Known-answer benchmarks across six datasets guard the behaviour
  (`tests/scientific/test_discovery_benchmarks.py`).
- Rankings can change when engines or penalties change. Such changes need an ADR and
  updated benchmarks.
