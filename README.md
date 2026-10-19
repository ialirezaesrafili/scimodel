# SciModel

**Find the equation behind your data, and know how far to trust it.**

SciModel is an open-source command-line assistant for scientists. Run it in a folder of
experimental data. It reads the files and profiles them, then suggests what you can do. It
searches established scientific laws, sparse regression, symbolic regression, and
(optionally) AI-proposed hypotheses for the equation that explains your measurements. Each
candidate is graded with a battery of statistical checks. You get a reproducible report
written for your level of expertise.

```text
$ cd ~/lab/catalysis && scimodel
Found 1 dataset(s):
  1) catalysis_arrhenius.csv — 64 rows; temperature, catalyst_loading, replicate, rate
I think the response is 'rate' and the candidate explanatory variable(s) are temperature, catalyst_loading.
  • 1 missing value(s); affected rows are excluded from fits. [rate]
  • temperature → rate: monotonic increasing, accelerating, exponential like

scimodel> how does rate depend on temperature and catalyst_loading
Best model: sparse_log_4  (sparse)
  rate = exp(w0 + w1*(1/temperature) + w2*log(catalyst_loading))
    w1 = -6941.4 ± 78      ← Arrhenius: Ea = −w1·R = 57.7 kJ/mol
    w2 = 0.806 ± 0.010     ← reaction order in catalyst
  R² = 0.9977, cross-validated R² = 0.9969
  Quality grade A (88/100)
Report written to scimodel_reports/catalysis_arrhenius-20261019-103252/report.md
```

## Why SciModel

- **Works on your data as it is.** It reads CSV, TSV, delimited text, JSON, Excel, and
  Parquet. Units in headers (`temperature [K]`), missing values, replicates, metadata columns,
  and decimal commas are all handled. Source values are never modified.
- **Discovers equations, not just fits them.** About 20 mechanistic and empirical model
  families run alongside sparse regression and genetic-programming symbolic regression. A
  neural network serves as a learnable-signal ceiling. It rediscovers Kepler's third law,
  the Arrhenius law, and Gompertz growth from data (see the
  [benchmarks](docs/how-it-works.md#validation-benchmarks)).
- **Honest model selection.** Candidates are ranked by search-adjusted AICc with Akaike
  weights, a parsimony guard, and cross-validation. Statistically tied candidates are shown
  as tied.
- **Quality you can read.** Up to 14 checks cover residual structure, lack of fit against
  replicates, identifiability, outliers, plausibility, and the neural ceiling. Each check
  comes with a plain-language explanation and an A–D grade.
- **For every level.** Novice, intermediate, and expert modes change the explanations, not
  the science.
- **AI that cannot invent results.** Claude or a local Ollama model can propose hypotheses
  and explain results. Every proposed formula passes an AST safety whitelist and is fitted
  locally. By default the model sees only summary statistics.
- **Scales to a whole lab.** A Go batch runner analyzes hundreds of datasets in parallel,
  incrementally.
- **Reproducible.** Every run records input SHA-256, settings, seed, and software versions.

## Install

```bash
pip install "scimodel[all]"        # core + Claude + plots + Excel
# or a minimal install: pip install scimodel
```

From source, with the full developer toolchain (Python, Go, Bash):

```bash
git clone https://github.com/REPLACE_WITH_OWNER/scimodel && cd scimodel
scripts/setup.sh
```

## Use

```bash
scimodel                                  # interactive assistant in the current folder
scimodel scan ~/lab                       # which files can be analyzed?
scimodel suggest data.csv                 # what can I do with this dataset?
scimodel discover data.csv --target rate --predictors temperature,loading
scimodel discover data.csv --formula "Vmax*s/(K + s)"   # test your own hypothesis
scripts/batch.sh ~/lab -workers 8         # every dataset, in parallel
```

Optional AI assistance (never required):

```bash
scimodel config set llm_provider anthropic    # uses ANTHROPIC_API_KEY or `ant auth login`
scimodel config set llm_provider ollama       # fully local; no data leaves the machine
```

## Documentation

| Guide | For |
|---|---|
| [Getting started](docs/getting-started.md) | Installing, your first session, reading a report |
| [How it works](docs/how-it-works.md) | The discovery pipeline, ranking, quality checks, AI guardrails, benchmarks |
| [CLI reference](docs/cli-reference.md) | Every command, option, setting, and exit code |
| [Architecture](docs/architecture.md) | Layers, components, the Python/Go/Bash split, extension points |
| [Development](docs/development.md) | Workflow scripts, testing, coverage, releasing |
| [Decision records](docs/decisions/) | Why things are the way they are |

## Scientific principles

SciModel supports scientific reasoning; it does not replace it. A good fit does not prove a
mechanism. Every report states its assumptions and limitations. When the data cannot
separate competing models, SciModel says so and suggests an experiment that could.

## License and citation

Apache-2.0. If SciModel contributes to your work, please cite it using
[`CITATION.cff`](CITATION.cff).
