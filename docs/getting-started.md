# Getting started

## 1. Install

SciModel needs Python 3.11 or newer.

```bash
pip install "scimodel[all]"
```

| Extra | Adds |
|---|---|
| `claude` | Claude as an optional reasoning assistant (`anthropic` SDK) |
| `plots` | Figures in reports (`matplotlib`) |
| `excel` | `.xlsx` input (`openpyxl`) |
| `all` | All of the above |

The parallel batch runner is a single Go binary. Download it from the GitHub release, or
build it with `scripts/build.sh --go-only` (requires Go 1.22+).

## 2. Put your data in a folder

Any table works: one row per observation, one column per variable. SciModel understands:

- **Units in headers:** `temperature [K]`, `time (h)`, `rate [mmol/(g*h)]`
- **Missing values:** empty, `NA`, `NaN`, `null`, `-`; affected rows are excluded and reported
- **Replicates:** repeated settings enable a lack-of-fit test against measurement noise
- **Metadata columns:** run IDs, wells, and operators are recognised and are not used as predictors
- **Comment lines** starting with `#`, `%` or `//`, and decimal commas in delimited text

## 3. Start the assistant

```bash
cd my-experiment
scimodel
```

On first use, SciModel asks how familiar you are with modeling. It remembers the answer;
change it later with `/level`.

| Level | What changes |
|---|---|
| `novice` | Plain-language explanations of every check, a glossary, fewer tables |
| `intermediate` | Technical detail with short explanations (default) |
| `expert` | Full statistics, all candidate expressions, minimal commentary |

The assistant then:

1. **Scans the folder** and lists the files it can analyze.
2. **Profiles the data.** It infers the response and the explanatory variables, flags
   quality issues, and describes each relationship's shape (saturating, sigmoidal,
   power-law-like, oscillating, …).
3. **Suggests next steps.** Type a number, describe your goal in your own words ("how does
   rate depend on temperature?"), or use a command:

| Command | Action |
|---|---|
| `/discover` | Search for the governing equation |
| `/fit A*x/(K + x)` | Test your own formula against the discovered ones |
| `/report` | Write a report for the latest result |
| `/data` | Switch dataset |
| `/suggest` | Show suggestions again |
| `/level expert` | Change the explanation level |
| `/help`, `/quit` | Help, exit |

When a language model is configured, a line ending in `?` is answered by the AI with the
current data profile and results as context.

## 4. Read the report

Reports go to `scimodel_reports/<dataset>-<timestamp>/`:

| File | Contents |
|---|---|
| `report.md` | Summary, data overview, recommended model with uncertainties, quality checks, candidate table, neural ceiling, next steps |
| `results.json` | Every candidate, parameter, standard error, criterion, and check, machine-readable |
| `run_manifest.json` | Input SHA-256, settings, seed, and software versions for reproduction |
| `figures/` | Data with fit, residuals, accuracy–complexity front (requires the `plots` extra) |

How to read the key numbers:

- **Quality grade A–D**: a weighted summary of all checks. A grade below B always lists the
  failed checks and what they mean.
- **ΔAICc and Akaike weight**: how much better the best model is than each alternative.
  ΔAICc below 2 means the data cannot tell the models apart. The report then suggests a
  discriminating experiment.
- **Cross-validated R²**: accuracy on data the model did not see during fitting. A large
  gap to the ordinary R² means overfitting.
- **Neural ceiling**: how well a flexible neural network predicts the same data. If it is
  clearly better than the equation, there is structure the equation misses.

## 5. Without the interactive session

```bash
scimodel discover data.csv                         # infer target and predictors
scimodel discover data.csv --target y --predictors x1,x2 --level novice
scimodel discover data.csv --formula "k*exp(-E/T)" --engines library,user --json
```

See the [CLI reference](cli-reference.md) for all options.

## 6. Optional: AI assistance

SciModel works fully offline. A language model adds hypothesis generation, interpretation
of free-text goals, and narrative explanations:

```bash
# Claude (credentials from ANTHROPIC_API_KEY or `ant auth login`; SciModel never stores keys)
pip install "scimodel[claude]"
scimodel config set llm_provider anthropic

# A local model through Ollama — nothing leaves your machine
ollama pull llama3.1
scimodel config set llm_provider ollama
scimodel llm status --test
```

By default, only summary statistics (column names, ranges, shapes) are sent, never raw
rows. Pass `--share-sample` or set `share_data_sample = true` to allow up to 25 rows.
