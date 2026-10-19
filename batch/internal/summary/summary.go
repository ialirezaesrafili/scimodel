// Package summary aggregates batch results into JSON and Markdown and supports incremental runs.
package summary

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"time"

	"scimodel/batch/internal/runner"
)

// Version of the batch summary schema.
const Version = "1"

// Row is the compact, cross-dataset view of one result.
type Row struct {
	Dataset      string  `json:"dataset"`
	SHA256       string  `json:"sha256"`
	Status       string  `json:"status"`
	Target       string  `json:"target,omitempty"`
	Predictors   string  `json:"predictors,omitempty"`
	BestModel    string  `json:"best_model,omitempty"`
	Expression   string  `json:"expression,omitempty"`
	RSquared     float64 `json:"r_squared,omitempty"`
	CVRSquared   float64 `json:"cv_r_squared,omitempty"`
	Grade        string  `json:"grade,omitempty"`
	Report       string  `json:"report,omitempty"`
	Seconds      float64 `json:"seconds"`
	Error        string  `json:"error,omitempty"`
	Observations int     `json:"observations,omitempty"`
}

// Summary is the document written to batch_summary.json.
type Summary struct {
	Version   string         `json:"summary_version"`
	Generated string         `json:"generated_at_utc"`
	Root      string         `json:"root"`
	Workers   int            `json:"workers"`
	Rows      []Row          `json:"rows"`
	Counts    map[string]int `json:"counts"`
}

// Build converts runner results into a summary.
func Build(root string, workers int, results []runner.Result) Summary {
	rows := make([]Row, 0, len(results))
	counts := map[string]int{}
	for _, result := range results {
		row := Row{
			Dataset: result.File.Relative,
			SHA256:  result.File.SHA256,
			Status:  result.Status,
			Seconds: round(result.Seconds),
			Error:   result.Error,
		}
		if result.Discovery != nil {
			fill(&row, result.Discovery)
		}
		counts[row.Status]++
		rows = append(rows, row)
	}
	sort.Slice(rows, func(i, j int) bool { return rows[i].Dataset < rows[j].Dataset })
	return Summary{
		Version:   Version,
		Generated: time.Now().UTC().Format(time.RFC3339),
		Root:      root,
		Workers:   workers,
		Rows:      rows,
		Counts:    counts,
	}
}

func fill(row *Row, discovery map[string]any) {
	row.Target, _ = discovery["target"].(string)
	if predictors, ok := discovery["predictors"].([]any); ok {
		names := make([]string, 0, len(predictors))
		for _, item := range predictors {
			if name, ok := item.(string); ok {
				names = append(names, name)
			}
		}
		row.Predictors = strings.Join(names, ",")
	}
	if n, ok := discovery["observations"].(float64); ok {
		row.Observations = int(n)
	}
	row.BestModel, _ = discovery["best"].(string)
	if candidates, ok := discovery["candidates"].([]any); ok && len(candidates) > 0 {
		if best, ok := candidates[0].(map[string]any); ok {
			row.Expression, _ = best["expression"].(string)
			if cv, ok := best["cv_r_squared"].(float64); ok {
				row.CVRSquared = cv
			}
			if fit, ok := best["fit"].(map[string]any); ok {
				if metrics, ok := fit["metrics"].(map[string]any); ok {
					row.RSquared, _ = metrics["r_squared"].(float64)
				}
			}
		}
	}
	if quality, ok := discovery["quality"].(map[string]any); ok {
		if assessment, ok := quality[row.BestModel].(map[string]any); ok {
			row.Grade, _ = assessment["grade"].(string)
		}
	}
	if report, ok := discovery["report"].(map[string]any); ok {
		row.Report, _ = report["report"].(string)
	}
}

// Write stores batch_summary.json and batch_summary.md in dir.
func Write(dir string, summary Summary) (string, string, error) {
	if err := os.MkdirAll(dir, 0o755); err != nil {
		return "", "", err
	}
	jsonPath := filepath.Join(dir, "batch_summary.json")
	data, err := json.MarshalIndent(summary, "", "  ")
	if err != nil {
		return "", "", err
	}
	if err := os.WriteFile(jsonPath, append(data, '\n'), 0o644); err != nil {
		return "", "", err
	}
	markdownPath := filepath.Join(dir, "batch_summary.md")
	return jsonPath, markdownPath, os.WriteFile(markdownPath, []byte(Markdown(summary)), 0o644)
}

// Markdown renders a human-readable cross-dataset table.
func Markdown(summary Summary) string {
	var b strings.Builder
	fmt.Fprintf(&b, "# SciModel batch summary\n\nRoot: `%s` · workers: %d · generated %s\n\n",
		summary.Root, summary.Workers, summary.Generated)
	keys := make([]string, 0, len(summary.Counts))
	for key := range summary.Counts {
		keys = append(keys, key)
	}
	sort.Strings(keys)
	for _, key := range keys {
		fmt.Fprintf(&b, "- %s: %d\n", key, summary.Counts[key])
	}
	b.WriteString("\n| Dataset | Status | Target | Best model | R² | CV R² | Grade | Seconds |\n")
	b.WriteString("|---|---|---|---|---:|---:|---|---:|\n")
	for _, row := range summary.Rows {
		fmt.Fprintf(&b, "| %s | %s | %s | %s | %s | %s | %s | %.1f |\n", row.Dataset, row.Status,
			row.Target, row.BestModel, number(row.RSquared), number(row.CVRSquared), row.Grade,
			row.Seconds)
	}
	for _, row := range summary.Rows {
		if row.Error != "" {
			fmt.Fprintf(&b, "\n- `%s`: %s", row.Dataset, row.Error)
		}
	}
	b.WriteString("\n")
	return b.String()
}

// LoadPrevious reads an earlier summary to skip unchanged, successful datasets.
func LoadPrevious(dir string) map[string]Row {
	previous := map[string]Row{}
	data, err := os.ReadFile(filepath.Join(dir, "batch_summary.json"))
	if err != nil {
		return previous
	}
	var summary Summary
	if json.Unmarshal(data, &summary) != nil {
		return previous
	}
	for _, row := range summary.Rows {
		if row.Status == "ok" || row.Status == "cached" {
			previous[row.Dataset] = row
		}
	}
	return previous
}

func number(value float64) string {
	if value == 0 {
		return ""
	}
	return fmt.Sprintf("%.4f", value)
}

func round(value float64) float64 {
	return float64(int(value*100+0.5)) / 100
}
