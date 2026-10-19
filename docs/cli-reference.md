# CLI reference

`scimodel` with no arguments, in an interactive terminal, starts the assistant
(`scimodel start .`). In scripts or pipes it prints help.

## Discovery commands

### `scimodel start [folder]`

Interactive assistant. See [Getting started](getting-started.md#3-start-the-assistant)
for session commands. Options: `--llm {none,anthropic,ollama}`, `--llm-model NAME`,
`--share-sample`.

### `scimodel scan [folder] [--json]`

Lists supported files (`.csv .tsv .txt .dat .json .xlsx .parquet`) up to three folders
deep, skipping virtual environments, VCS folders and report folders. A file is *ready* when
it parses and has at least two numeric columns.

### `scimodel profile <file> [--target COL] [--predictors A,B] [--json]`

Column types, units, roles and ranges; inferred response and predictors; relationship
shape hints; data-quality issues.

### `scimodel suggest <file> [--level LEVEL] [--json]`

Prioritized actions with rationale and the exact command to run.

### `scimodel discover <file> [options]`

| Option | Default | Meaning |
|---|---|---|
| `--target COL` | inferred | Response variable |
| `--predictors A,B` | inferred | Explanatory variables |
| `--formula EXPR` | — | Your own hypothesis; repeatable. Free symbols become parameters |
| `--engines LIST` | `library,sparse,symbolic,neural,llm` | Engines to run (`llm` is skipped when no provider is configured) |
| `--objective TEXT` | — | Research goal; passed to the language model |
| `--seed N` | setting `seed` (0) | Reproducibility seed |
| `--time-budget S` | setting `time_budget` (15) | Seconds for symbolic search |
| `--level LEVEL` | setting `level` | `novice`, `intermediate`, `expert` |
| `--output-dir DIR` | `scimodel_reports/<name>-discovery` | Report bundle location |
| `--no-report` | — | Do not write files |
| `--explain` | — | Add an AI interpretation section (needs a provider) |
| `--json` | — | Print the full `DiscoveryResult` (plus report paths) as JSON on stdout; progress is suppressed |
| `--llm`, `--llm-model`, `--share-sample` | settings | Language-model overrides |

The JSON output schema matches `results.json` and is what the Go batch runner consumes.

### `scimodel config show` / `scimodel config set KEY VALUE [--project]`

| Setting | Default | Meaning |
|---|---|---|
| `level` | `intermediate` | Explanation level |
| `llm_provider` | `none` | `none`, `anthropic`, `ollama` |
| `llm_model` | provider default | e.g. `claude-opus-5-5`, `llama3.1` |
| `ollama_host` | `http://localhost:11434` | Ollama server |
| `share_data_sample` | `false` | Allow up to 25 raw rows in LLM prompts |
| `reports_dir` | `scimodel_reports` | Where interactive reports go |
| `time_budget` | `15` | Symbolic-search seconds |
| `seed` | `0` | Default seed |
| `onboarded` | `false` | Set after the first-run level question |

Precedence: environment `SCIMODEL_<KEY>` > `./.scimodel/config.toml` (with `--project`) >
`$XDG_CONFIG_HOME/scimodel/config.toml` > defaults. Credentials are never stored. Claude
reads `ANTHROPIC_API_KEY` or an `ant auth login` profile.

### `scimodel llm status [--test]`

Shows the configured provider and model. `--test` sends one short request.

## Batch runner: `scimodel-batch`

```bash
scimodel-batch -root ~/lab -out ~/lab/scimodel_reports/batch -workers 8 -timeout 10m \
               -args "--time-budget 30 --engines library,sparse,symbolic"
# or: scripts/batch.sh ~/lab -workers 8
```

| Flag | Default | Meaning |
|---|---|---|
| `-root` | `.` | Folder to scan |
| `-out` | `scimodel_reports/batch` | Reports + `batch_summary.{json,md}` |
| `-workers` | CPUs/2 | Parallel jobs |
| `-timeout` | `10m` | Per-dataset limit |
| `-depth` | `3` | Folder depth |
| `-scimodel` | `scimodel` | Command to invoke (may contain spaces, e.g. `python -m scimodel`) |
| `-args` | — | Extra `discover` arguments |
| `-incremental` | `true` | Skip unchanged datasets that succeeded before |
| `-dry-run` | `false` | List datasets and fingerprints only |
| `-version` | — | Print version |

## Kinetics workflow commands (since 0.1)

The original enzyme-kinetics workflow is unchanged. These commands default to columns
`substrate_conc` and `reaction_velocity` (override with `--x-column`/`--y-column`) and print
JSON.

| Command | Purpose |
|---|---|
| `data inspect <csv>` | Kinetics-specific data validation |
| `model fit <csv>` / `model validate <csv>` | Bounded Michaelis–Menten fit / validation checks |
| `formula recommend <csv> --objective TEXT` | Rule-based formula recommendations |
| `formula fit <csv> --formula EXPR [--params N:lo:hi,...] [--backend scipy\|matlab] [--fallback-to-scipy]` | Fit one formula, optionally with MATLAB |
| `formula compare <csv>` | Fit and compare the recommended formulas (AIC/BIC) |
| `report build <csv> --output-dir DIR` | Kinetics report bundle |
| `assistant run <csv> --goal TEXT [--mode normal\|verbose\|audit] [--provider-plan plan.json]` | Audited plan→tools→verify workflow |
| `assistant history \| show ID \| compare A B` | Stored run records |
| `assistant context set\|list\|show\|remove` | Reviewable personal/project context |
| `assistant recommendation list\|show\|accept\|reject\|correct` | Recommendation review lifecycle |
| `assistant evaluate [--compare A B]` | Assistant benchmark suite |

## Exit codes

| Code | Meaning |
|---|---|
| 0 | Success |
| 2 | Invalid input, arguments, data, or configuration (message on stderr); for kinetics commands also a failed validation |
| 3 | `scimodel-batch` only: at least one job failed, timed out, or was cancelled |
