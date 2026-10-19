// Command scimodel-batch analyzes every dataset under a folder concurrently.
//
// It discovers data files, fingerprints them in parallel, skips datasets whose
// content is unchanged since the last successful run (-incremental), and runs
// `scimodel discover` on the rest with a bounded worker pool, per-job timeouts,
// and graceful cancellation on Ctrl-C. Results are aggregated into
// batch_summary.json and batch_summary.md.
package main

import (
	"context"
	"flag"
	"fmt"
	"os"
	"os/signal"
	"path/filepath"
	"runtime"
	"strings"
	"syscall"
	"time"

	"scimodel/batch/internal/runner"
	"scimodel/batch/internal/summary"
	"scimodel/batch/internal/workspace"
)

var version = "dev"

func main() {
	os.Exit(run(os.Args[1:]))
}

func run(arguments []string) int {
	flags := flag.NewFlagSet("scimodel-batch", flag.ContinueOnError)
	root := flags.String("root", ".", "folder to scan for datasets")
	out := flags.String("out", "scimodel_reports/batch", "folder for reports and the summary")
	workers := flags.Int("workers", max(1, runtime.NumCPU()/2), "parallel discovery jobs")
	timeout := flags.Duration("timeout", 10*time.Minute, "time limit per dataset")
	depth := flags.Int("depth", 3, "maximum folder depth")
	command := flags.String("scimodel", "scimodel", "scimodel command (space-separated)")
	extra := flags.String("args", "", "extra arguments for `scimodel discover` (space-separated)")
	incremental := flags.Bool("incremental", true, "skip unchanged datasets that succeeded before")
	dryRun := flags.Bool("dry-run", false, "list datasets without analyzing them")
	showVersion := flags.Bool("version", false, "print version and exit")
	if err := flags.Parse(arguments); err != nil {
		return 2
	}
	if *showVersion {
		fmt.Println("scimodel-batch", version)
		return 0
	}

	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()

	files, err := workspace.Scan(*root, *depth, 200_000_000)
	if err != nil {
		fmt.Fprintln(os.Stderr, "scan failed:", err)
		return 1
	}
	if len(files) == 0 {
		fmt.Fprintln(os.Stderr, "no supported data files found under", *root)
		return 0
	}
	if err := workspace.Fingerprint(ctx, files, runtime.NumCPU()); err != nil {
		fmt.Fprintln(os.Stderr, "fingerprinting failed:", err)
		return 1
	}
	if *dryRun {
		for _, file := range files {
			fmt.Printf("%s\t%d bytes\t%s\n", file.Relative, file.Size, file.SHA256[:12])
		}
		return 0
	}

	outDir, _ := filepath.Abs(*out)
	previous := map[string]summary.Row{}
	if *incremental {
		previous = summary.LoadPrevious(outDir)
	}
	var jobs []runner.Job
	var cached []runner.Result
	for _, file := range files {
		if row, ok := previous[file.Relative]; ok && row.SHA256 == file.SHA256 {
			cached = append(cached, cachedResult(file, row))
			continue
		}
		jobs = append(jobs, runner.Job{File: file, OutputDir: runner.OutputDirFor(outDir, file)})
	}
	fmt.Fprintf(os.Stderr, "%d dataset(s): %d to analyze, %d unchanged; %d worker(s)\n",
		len(files), len(jobs), len(cached), *workers)

	pool := runner.Pool{
		Workers:  *workers,
		Timeout:  *timeout,
		Executor: runner.CommandExecutor{Command: strings.Fields(*command), Args: strings.Fields(*extra)},
		Progress: func(done, total int, result runner.Result) {
			fmt.Fprintf(os.Stderr, "[%d/%d] %-8s %s (%.1fs)\n", done, total, result.Status,
				result.File.Relative, result.Seconds)
		},
	}
	results := append(pool.Run(ctx, jobs), cached...)
	rootDir, _ := filepath.Abs(*root)
	document := summary.Build(rootDir, *workers, results)
	jsonPath, markdownPath, err := summary.Write(outDir, document)
	if err != nil {
		fmt.Fprintln(os.Stderr, "writing summary failed:", err)
		return 1
	}
	fmt.Fprintf(os.Stderr, "summary: %s\n         %s\n", jsonPath, markdownPath)
	if document.Counts["failed"]+document.Counts["timeout"]+document.Counts["cancelled"] > 0 {
		return 3
	}
	return 0
}

func cachedResult(file workspace.File, row summary.Row) runner.Result {
	return runner.Result{
		File:   file,
		Status: "cached",
		Discovery: map[string]any{
			"target":       row.Target,
			"predictors":   splitAny(row.Predictors),
			"observations": float64(row.Observations),
			"best":         row.BestModel,
			"candidates": []any{map[string]any{
				"expression":   row.Expression,
				"cv_r_squared": row.CVRSquared,
				"fit":          map[string]any{"metrics": map[string]any{"r_squared": row.RSquared}},
			}},
			"quality": map[string]any{row.BestModel: map[string]any{"grade": row.Grade}},
			"report":  map[string]any{"report": row.Report},
		},
	}
}

func splitAny(value string) []any {
	var items []any
	for _, item := range strings.Split(value, ",") {
		if item != "" {
			items = append(items, item)
		}
	}
	return items
}
