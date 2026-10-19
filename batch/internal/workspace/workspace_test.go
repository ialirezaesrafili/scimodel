package workspace

import (
	"context"
	"os"
	"path/filepath"
	"testing"
)

func write(t *testing.T, path, content string) {
	t.Helper()
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(path, []byte(content), 0o644); err != nil {
		t.Fatal(err)
	}
}

func TestScanAndFingerprint(t *testing.T) {
	root := t.TempDir()
	write(t, filepath.Join(root, "a.csv"), "x,y\n1,2\n")
	write(t, filepath.Join(root, "sub", "b.tsv"), "x\ty\n1\t2\n")
	write(t, filepath.Join(root, "notes.md"), "ignored")
	write(t, filepath.Join(root, ".venv", "c.csv"), "ignored")
	write(t, filepath.Join(root, "scimodel_reports", "results.json"), "{}")
	write(t, filepath.Join(root, "d1", "d2", "d3", "d4", "deep.csv"), "x,y\n")

	files, err := Scan(root, 3, 1<<20)
	if err != nil {
		t.Fatal(err)
	}
	if len(files) != 2 || files[0].Relative != "a.csv" || files[1].Relative != filepath.Join("sub", "b.tsv") {
		t.Fatalf("unexpected files: %+v", files)
	}
	if err := Fingerprint(context.Background(), files, 4); err != nil {
		t.Fatal(err)
	}

	if len(files[0].SHA256) != 64 {
		t.Fatalf("bad digest %q", files[0].SHA256)
	}
	if files[0].SHA256 == files[1].SHA256 {
		t.Fatal("different contents must have different digests")
	}
}
