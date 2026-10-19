package summary

import (
	"os"
	"strings"
	"testing"

	"scimodel/batch/internal/runner"
	"scimodel/batch/internal/workspace"
)

func TestBuildWriteAndReload(t *testing.T) {
	discovery := map[string]any{
		"target": "rate", "predictors": []any{"temperature", "loading"}, "observations": 63.0,
		"best": "arrhenius",
		"candidates": []any{map[string]any{
			"expression": "k*exp(-E/T)", "cv_r_squared": 0.99,
			"fit": map[string]any{"metrics": map[string]any{"r_squared": 0.995}},
		}},
		"quality": map[string]any{"arrhenius": map[string]any{"grade": "A"}},
		"report":  map[string]any{"report": "/out/a/report.md"},
	}
	results := []runner.Result{
		{File: workspace.File{Relative: "b.csv", SHA256: "bb"}, Status: "failed", Error: "boom"},
		{File: workspace.File{Relative: "a.csv", SHA256: "aa"}, Status: "ok", Discovery: discovery},
	}
	document := Build("/out", 2, results)
	if document.Rows[0].Dataset != "a.csv" || document.Rows[0].Grade != "A" ||
		document.Rows[0].Predictors != "temperature,loading" || document.Rows[0].RSquared != 0.995 {
		t.Fatalf("unexpected row: %+v", document.Rows[0])
	}
	if document.Counts["ok"] != 1 || document.Counts["failed"] != 1 {
		t.Fatalf("unexpected counts: %+v", document.Counts)
	}
	dir := t.TempDir()
	_, markdownPath, err := Write(dir, document)
	if err != nil {
		t.Fatal(err)
	}
	markdown, _ := os.ReadFile(markdownPath)
	if !strings.Contains(string(markdown), "| a.csv | ok | rate | arrhenius |") ||
		!strings.Contains(string(markdown), "`b.csv`: boom") {
		t.Fatalf("unexpected markdown:\n%s", markdown)
	}
	previous := LoadPrevious(dir)
	if _, ok := previous["a.csv"]; !ok || len(previous) != 1 {
		t.Fatalf("only successful rows should be reusable: %+v", previous)
	}
}
