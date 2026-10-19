# Changelog

All notable changes to SciModel are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [1.0.0rc1] - 2026-10-19

First production release candidate: from a single kinetics model to a general scientific
modeling assistant.

### Added

- Interactive assistant: `scimodel` in a data folder scans files, profiles them, suggests
  analyses, interprets free-text goals, runs discovery, and writes reports, with novice,
  intermediate and expert explanation levels.
- Commands `start`, `scan`, `profile`, `suggest`, `discover`, `config`, `llm`.
- Multi-format reader (CSV, TSV, delimited text, JSON, Excel, Parquet) with header units,
  missing-value tokens, comments and decimal commas.
- Discovery engines: model library (~20 scientific laws), sparse regression (raw and
  log target), genetic-programming symbolic regression, LLM hypotheses, user formulas.
- Ranking by search-adjusted AICc with Akaike weights, parsimony guard, and mechanistic
  tie-break; Pareto front; k-fold cross-validation.
- Quality assessment (14 checks) with A–D grades and plain-language explanations; NumPy
  neural-network ceiling.
- Optional language models: Claude (official SDK, structured outputs, refusal fallback)
  and local Ollama; profile-only context by default.
- Discovery report bundle: Markdown, `results.json`, manifest, figures.
- Go `scimodel-batch`: concurrent, incremental, timeout-aware batch analysis.
- Bash workflow scripts and CI jobs for Python, Go, shell and an end-to-end smoke test;
  tag-driven release workflow with cross-compiled binaries.
- Realistic example datasets with documented ground truth and known-answer benchmarks.

### Changed

- `ScipyFormulaSolver` accepts several independent variables, multi-start initial
  values, robust losses and Jacobian scaling, and returns parameter correlations.
- Formula whitelist extended (`expm1`, `log2`, `log1p`, `tan`, `arctan`, `sinh`, `cosh`,
  `pi`); validated syntax trees are cached.
- Documentation consolidated into five guides; phase reports and the roadmap were removed
  (available in git history).

## [0.1.0] - 2026-10-18

- Enzyme-kinetics workflow: CSV inspection, bounded Michaelis–Menten fit, validation,
  reproducible reports, assistant with audit trail, context, recommendations and
  evaluation suite, AST-safe formula fitting with an optional MATLAB backend.
