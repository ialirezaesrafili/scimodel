// Package runner executes SciModel discovery jobs concurrently with bounded parallelism.
package runner

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"os/exec"
	"path/filepath"
	"strings"
	"sync"
	"time"

	"scimodel/batch/internal/workspace"
)

// Job is one dataset to analyze.
type Job struct {
	File      workspace.File
	OutputDir string
}

// Result is the outcome of one job. Discovery holds the decoded JSON from
// `scimodel discover --json` when the job succeeded.
type Result struct {
	File      workspace.File `json:"file"`
	Status    string         `json:"status"` // ok | failed | timeout | cached | cancelled
	Seconds   float64        `json:"seconds"`
	Error     string         `json:"error,omitempty"`
	OutputDir string         `json:"output_dir"`
	Discovery map[string]any `json:"discovery,omitempty"`
	Stderr    string         `json:"stderr,omitempty"`
}

// Executor runs one job; it is an interface so the pool can be tested without Python.
type Executor interface {
	Execute(ctx context.Context, job Job) ([]byte, []byte, error)
}

// CommandExecutor shells out to the scimodel CLI.
type CommandExecutor struct {
	Command []string // e.g. ["scimodel"] or ["python", "-m", "scimodel"]
	Args    []string // extra arguments appended to `discover`
}

// Execute runs `scimodel discover <file> --json --output-dir <dir> ...`.
func (c CommandExecutor) Execute(ctx context.Context, job Job) ([]byte, []byte, error) {
	if len(c.Command) == 0 {
		return nil, nil, errors.New("no scimodel command configured")
	}
	args := append([]string{}, c.Command[1:]...)
	args = append(args, "discover", job.File.Path, "--json", "--output-dir", job.OutputDir)
	args = append(args, c.Args...)
	cmd := exec.CommandContext(ctx, c.Command[0], args...)
	var stdout, stderr bytes.Buffer
	cmd.Stdout, cmd.Stderr = &stdout, &stderr
	err := cmd.Run()
	return stdout.Bytes(), stderr.Bytes(), err
}

// Pool runs jobs with a fixed number of workers and a per-job timeout.
type Pool struct {
	Workers  int
	Timeout  time.Duration
	Executor Executor
	// Progress, when set, receives one line per finished job (called from workers).
	Progress func(done, total int, result Result)
}

// Run executes every job and returns results in the order of the input jobs.
func (p Pool) Run(ctx context.Context, jobs []Job) []Result {
	workers := p.Workers
	if workers < 1 {
		workers = 1
	}
	results := make([]Result, len(jobs))
	queue := make(chan int)
	var wg sync.WaitGroup
	var mu sync.Mutex
	done := 0
	for w := 0; w < workers; w++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			for index := range queue {
				results[index] = p.runOne(ctx, jobs[index])
				if p.Progress != nil {
					mu.Lock()
					done++
					p.Progress(done, len(jobs), results[index])
					mu.Unlock()
				}
			}
		}()
	}
dispatch:
	for index := range jobs {
		select {
		case queue <- index:
		case <-ctx.Done():
			for rest := index; rest < len(jobs); rest++ {
				results[rest] = Result{File: jobs[rest].File, Status: "cancelled",
					OutputDir: jobs[rest].OutputDir, Error: ctx.Err().Error()}
			}
			break dispatch
		}
	}
	close(queue)
	wg.Wait()
	return results
}

func (p Pool) runOne(parent context.Context, job Job) Result {
	ctx, cancel := parent, context.CancelFunc(func() {})
	if p.Timeout > 0 {
		ctx, cancel = context.WithTimeout(parent, p.Timeout)
	}
	defer cancel()
	started := time.Now()
	stdout, stderr, err := p.Executor.Execute(ctx, job)
	result := Result{
		File:      job.File,
		Seconds:   time.Since(started).Seconds(),
		OutputDir: job.OutputDir,
		Stderr:    tail(string(stderr), 2000),
	}
	switch {
	case errors.Is(ctx.Err(), context.DeadlineExceeded):
		result.Status, result.Error = "timeout", fmt.Sprintf("exceeded %s", p.Timeout)
	case parent.Err() != nil:
		result.Status, result.Error = "cancelled", parent.Err().Error()
	case err != nil:
		result.Status, result.Error = "failed", strings.TrimSpace(lastLine(string(stderr), err))
	default:
		var payload map[string]any
		if jsonErr := json.Unmarshal(stdout, &payload); jsonErr != nil {
			result.Status, result.Error = "failed", "invalid JSON from scimodel: "+jsonErr.Error()
		} else {
			result.Status, result.Discovery = "ok", payload
		}
	}
	return result
}

// OutputDirFor maps a dataset to a stable, collision-free report directory.
func OutputDirFor(root string, file workspace.File) string {
	name := strings.TrimSuffix(file.Relative, filepath.Ext(file.Relative))
	name = strings.NewReplacer(string(filepath.Separator), "__", " ", "_").Replace(name)
	return filepath.Join(root, name)
}

func tail(text string, limit int) string {
	if len(text) <= limit {
		return text
	}
	return text[len(text)-limit:]
}

func lastLine(stderr string, err error) string {
	lines := strings.Split(strings.TrimSpace(stderr), "\n")
	if len(lines) > 0 && strings.TrimSpace(lines[len(lines)-1]) != "" {
		return lines[len(lines)-1]
	}
	return err.Error()
}
