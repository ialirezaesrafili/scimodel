// Package workspace finds data files and fingerprints them concurrently.
package workspace

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"io"
	"io/fs"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"sync"
)

// Supported mirrors scimodel.adapters.tabular_reader.SUPPORTED_SUFFIXES.
var Supported = map[string]bool{
	".csv": true, ".tsv": true, ".txt": true, ".dat": true,
	".json": true, ".xlsx": true, ".parquet": true,
}

// Ignored mirrors scimodel.application.workspace.IGNORED_DIRECTORIES.
var Ignored = map[string]bool{
	".git": true, ".venv": true, "venv": true, "env": true, "node_modules": true,
	"__pycache__": true, ".scimodel": true, "scimodel_reports": true, "dist": true,
	"build": true, ".ipynb_checkpoints": true, "site-packages": true,
}

// File is one candidate dataset with its content fingerprint.
type File struct {
	Path     string `json:"path"`
	Relative string `json:"relative"`
	Size     int64  `json:"size_bytes"`
	SHA256   string `json:"sha256"`
}

// Scan walks root up to maxDepth and returns supported files sorted by path.
func Scan(root string, maxDepth int, maxBytes int64) ([]File, error) {
	root, err := filepath.Abs(root)
	if err != nil {
		return nil, err
	}
	var files []File
	err = filepath.WalkDir(root, func(path string, entry fs.DirEntry, walkErr error) error {
		if walkErr != nil {
			return nil // unreadable entries are skipped, not fatal
		}
		relative, _ := filepath.Rel(root, path)
		depth := 0
		if relative != "." {
			depth = strings.Count(relative, string(filepath.Separator)) + 1
		}
		name := entry.Name()
		if entry.IsDir() {
			if path != root && (Ignored[name] || strings.HasPrefix(name, ".") || depth > maxDepth) {
				return filepath.SkipDir
			}
			return nil
		}
		if strings.HasPrefix(name, ".") || !Supported[strings.ToLower(filepath.Ext(name))] {
			return nil
		}
		if name == "results.json" || name == "run_manifest.json" || name == "batch_summary.json" {
			return nil
		}
		info, err := entry.Info()
		if err != nil || info.Size() > maxBytes {
			return nil
		}
		files = append(files, File{Path: path, Relative: relative, Size: info.Size()})
		return nil
	})
	sort.Slice(files, func(i, j int) bool { return files[i].Relative < files[j].Relative })
	return files, err
}

// Fingerprint computes SHA-256 digests with a bounded pool of goroutines.
func Fingerprint(ctx context.Context, files []File, workers int) error {
	if workers < 1 {
		workers = 1
	}
	jobs := make(chan int)
	errs := make(chan error, len(files))
	var wg sync.WaitGroup
	for w := 0; w < workers; w++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			for index := range jobs {
				digest, err := hashFile(files[index].Path)
				if err != nil {
					errs <- err
					continue
				}
				files[index].SHA256 = digest
			}
		}()
	}
	for index := range files {
		select {
		case jobs <- index:
		case <-ctx.Done():
			close(jobs)
			wg.Wait()
			return ctx.Err()
		}
	}
	close(jobs)
	wg.Wait()
	close(errs)
	return <-errs // nil when no error was sent
}

func hashFile(path string) (string, error) {
	handle, err := os.Open(path)
	if err != nil {
		return "", err
	}
	defer handle.Close()
	hasher := sha256.New()
	if _, err := io.Copy(hasher, handle); err != nil {
		return "", err
	}
	return hex.EncodeToString(hasher.Sum(nil)), nil
}
