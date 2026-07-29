#!/bin/sh
set -eu

repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)

clean_tree() {
  target=$1
  if [ -e "$target" ]; then
    find "$target" -depth -delete
  fi
}

clean_read_only_tree() {
  target=$1
  if [ -d "$target" ]; then
    find "$target" -type d -exec chmod u+rwx {} +
    find "$target" -type f -exec chmod u+rw {} +
  fi
  clean_tree "$target"
}

clean_tree "$repo_root/out/build/gcc-debug"
clean_tree "$repo_root/out/build/gcc-sanitizers"
clean_tree "$repo_root/out/build/clang-debug"
clean_tree "$repo_root/out/build/clang-sanitizers"
clean_tree "$repo_root/.cache/toolchain-linux-x86_64"
clean_tree "$repo_root/.cache/go-bootstrap"
clean_tree "$repo_root/.cache/go1.25.10"
clean_tree "$repo_root/.cache/go-build"
clean_tree "$repo_root/.cache/go-bin"
clean_read_only_tree "$repo_root/.cache/go-mod"

for python_root in "$repo_root/simulation" "$repo_root/tools" "$repo_root/tests"; do
  find "$python_root" -type f \
    \( -name '*.pyc' -o -name '*.pyo' \) -delete
  find "$python_root" -depth -type d -name __pycache__ -empty -delete
done

rmdir "$repo_root/out/build" 2>/dev/null || true
rmdir "$repo_root/out" 2>/dev/null || true
rmdir "$repo_root/.cache" 2>/dev/null || true

printf '%s\n' "Removed known reproducible local artifacts."
