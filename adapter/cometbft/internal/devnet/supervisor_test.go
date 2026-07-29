package devnet

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestEnsureSocketRoot(t *testing.T) {
	t.Run("create-and-protect", func(t *testing.T) {
		path := filepath.Join(t.TempDir(), "sockets")
		if err := ensureSocketRoot(path); err != nil {
			t.Fatalf("create socket root: %v", err)
		}
		info, err := os.Lstat(path)
		if err != nil {
			t.Fatal(err)
		}
		if !info.IsDir() || info.Mode().Perm() != 0o700 {
			t.Fatalf("socket root mode = %v", info.Mode())
		}
		if err := os.Chmod(path, 0o755); err != nil {
			t.Fatal(err)
		}
		if err := ensureSocketRoot(path); err != nil {
			t.Fatalf("protect existing socket root: %v", err)
		}
		info, err = os.Lstat(path)
		if err != nil {
			t.Fatal(err)
		}
		if info.Mode().Perm() != 0o700 {
			t.Fatalf("reprotected socket root mode = %v", info.Mode())
		}
	})

	t.Run("reject-file", func(t *testing.T) {
		path := filepath.Join(t.TempDir(), "sockets")
		if err := os.WriteFile(path, []byte("occupied"), 0o600); err != nil {
			t.Fatal(err)
		}
		err := ensureSocketRoot(path)
		if err == nil || !strings.Contains(err.Error(), "not a directory") {
			t.Fatalf("file error = %v", err)
		}
	})

	t.Run("reject-symlink", func(t *testing.T) {
		parent := t.TempDir()
		target := filepath.Join(parent, "target")
		if err := os.Mkdir(target, 0o700); err != nil {
			t.Fatal(err)
		}
		path := filepath.Join(parent, "sockets")
		if err := os.Symlink(target, path); err != nil {
			t.Fatal(err)
		}
		err := ensureSocketRoot(path)
		if err == nil || !strings.Contains(err.Error(), "symbolic link") {
			t.Fatalf("symlink error = %v", err)
		}
	})
}
