package runner

import (
	"context"
	"errors"
	"sync/atomic"
	"testing"
	"time"

	"scimodel/batch/internal/workspace"
)

type fakeExecutor struct {
	active, peak atomic.Int32
	delay        time.Duration
	fail         map[string]bool
}

func (f *fakeExecutor) Execute(ctx context.Context, job Job) ([]byte, []byte, error) {
	now := f.active.Add(1)
	defer f.active.Add(-1)
	for {
		peak := f.peak.Load()
		if now <= peak || f.peak.CompareAndSwap(peak, now) {
			break
		}
	}
	select {
	case <-time.After(f.delay):
	case <-ctx.Done():
		return nil, nil, ctx.Err()
	}
	if f.fail[job.File.Relative] {
		return nil, []byte("Traceback\nscimodel: error: bad data"), errors.New("exit status 2")
	}
	return []byte(`{"target":"y","best":"m","candidates":[{"expression":"a*x"}]}`), nil, nil
}

func jobs(names ...string) []Job {
	out := make([]Job, len(names))
	for i, name := range names {
		out[i] = Job{File: workspace.File{Relative: name}}
	}
	return out
}

func TestPoolRespectsWorkerLimitAndOrder(t *testing.T) {
	executor := &fakeExecutor{delay: 20 * time.Millisecond, fail: map[string]bool{"b": true}}
	pool := Pool{Workers: 3, Executor: executor}
	results := pool.Run(context.Background(), jobs("a", "b", "c", "d", "e", "f", "g"))
	if got := executor.peak.Load(); got > 3 || got < 2 {
		t.Fatalf("peak concurrency = %d, want between 2 and 3", got)
	}
	for i, name := range []string{"a", "b", "c", "d", "e", "f", "g"} {
		if results[i].File.Relative != name {
			t.Fatalf("result %d is %s, want %s", i, results[i].File.Relative, name)
		}
	}
	if results[0].Status != "ok" || results[0].Discovery["best"] != "m" {
		t.Fatalf("unexpected ok result: %+v", results[0])
	}
	if results[1].Status != "failed" || results[1].Error != "scimodel: error: bad data" {
		t.Fatalf("unexpected failed result: %+v", results[1])
	}
}

func TestPoolTimeout(t *testing.T) {
	pool := Pool{Workers: 2, Timeout: 10 * time.Millisecond, Executor: &fakeExecutor{delay: time.Second}}
	results := pool.Run(context.Background(), jobs("slow"))
	if results[0].Status != "timeout" {
		t.Fatalf("status = %s, want timeout", results[0].Status)
	}
}

func TestPoolCancellation(t *testing.T) {
	ctx, cancel := context.WithCancel(context.Background())
	cancel()
	pool := Pool{Workers: 1, Executor: &fakeExecutor{delay: time.Second}}
	for _, result := range pool.Run(ctx, jobs("a", "b", "c")) {
		if result.Status != "cancelled" {
			t.Fatalf("status = %s, want cancelled", result.Status)
		}
	}
}

func TestInvalidJSONIsFailure(t *testing.T) {
	pool := Pool{Workers: 1, Executor: executorFunc(func(context.Context, Job) ([]byte, []byte, error) {
		return []byte("not json"), nil, nil
	})}
	if result := pool.Run(context.Background(), jobs("x"))[0]; result.Status != "failed" {
		t.Fatalf("status = %s, want failed", result.Status)
	}
}

type executorFunc func(context.Context, Job) ([]byte, []byte, error)

func (f executorFunc) Execute(ctx context.Context, job Job) ([]byte, []byte, error) {
	return f(ctx, job)
}

func TestOutputDirFor(t *testing.T) {
	got := OutputDirFor("/out", workspace.File{Relative: "lab a/run 1.csv"})
	if got != "/out/lab_a__run_1" {
		t.Fatalf("got %s", got)
	}
}
