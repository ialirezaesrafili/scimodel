package main

import (
	"os"
	"path/filepath"
	"testing"
)

func TestDryRunAndEmptyFolder(t *testing.T) {
	root := t.TempDir()
	if code := run([]string{"-root", root}); code != 0 {
		t.Fatalf("empty folder exit = %d", code)
	}
	if err := os.WriteFile(filepath.Join(root, "a.csv"), []byte("x,y\n1,2\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	if code := run([]string{"-root", root, "-dry-run"}); code != 0 {
		t.Fatalf("dry run exit = %d", code)
	}
	if code := run([]string{"-version"}); code != 0 {
		t.Fatalf("version exit = %d", code)
	}
	if code := run([]string{"-unknown-flag"}); code != 2 {
		t.Fatalf("bad flag exit = %d", code)
	}
}

func TestMissingCommandFailsGracefully(t *testing.T) {
	root := t.TempDir()
	out := filepath.Join(root, "out")
	if err := os.WriteFile(filepath.Join(root, "a.csv"), []byte("x,y\n1,2\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	code := run([]string{"-root", root, "-out", out, "-scimodel", "definitely-not-installed-xyz"})
	if code != 3 {
		t.Fatalf("exit = %d, want 3 for failed jobs", code)
	}
	if _, err := os.Stat(filepath.Join(out, "batch_summary.json")); err != nil {
		t.Fatal("summary must be written even when jobs fail")
	}
}
