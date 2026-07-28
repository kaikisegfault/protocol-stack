#!/bin/sh
set -eu

repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
go_version=1.25.10
archive_name="go${go_version}.linux-amd64.tar.gz"
expected_sha256=42d4f7a32316aa66591eca7e89867256057a4264451aca10570a715b3637ba70
download_dir="$repo_root/.cache/go-bootstrap"
archive="$download_dir/$archive_name"
go_root="$repo_root/.cache/go${go_version}"

mkdir -p "$download_dir"
python3 - "$archive" "$expected_sha256" <<'PY'
import hashlib
import os
import pathlib
import sys
import urllib.request

archive = pathlib.Path(sys.argv[1])
expected = sys.argv[2]
url = f"https://go.dev/dl/{archive.name}"

def digest(path):
    value = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()

if not archive.exists() or digest(archive) != expected:
    temporary = archive.with_suffix(archive.suffix + ".tmp")
    try:
        with urllib.request.urlopen(url) as source, temporary.open("wb") as target:
            while chunk := source.read(1024 * 1024):
                target.write(chunk)
        if digest(temporary) != expected:
            raise RuntimeError("downloaded Go archive failed SHA-256 verification")
        os.replace(temporary, archive)
    finally:
        temporary.unlink(missing_ok=True)

if digest(archive) != expected:
    raise RuntimeError("cached Go archive failed SHA-256 verification")
PY

cached_version=
if [ -x "$go_root/bin/go" ]; then
  cached_version=$("$go_root/bin/go" version 2>/dev/null || true)
fi
if [ "$cached_version" != "go version go${go_version} linux/amd64" ]; then
  if [ -e "$go_root" ]; then
    find "$go_root" -depth -delete
  fi
  mkdir -p "$go_root"
  tar -xzf "$archive" --strip-components=1 -C "$go_root"
fi

actual_version=$("$go_root/bin/go" version)
if [ "$actual_version" != "go version go${go_version} linux/amd64" ]; then
  echo "unexpected Go toolchain identity: $actual_version" >&2
  exit 1
fi

printf '%s\n' "$go_root/bin/go"
