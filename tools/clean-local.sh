#!/bin/sh
set -eu

repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)

clean_tree() {
  target=$1
  if [ -e "$target" ]; then
    find "$target" -depth -delete
  fi
}

clean_tree "$repo_root/out/build/gcc-debug"
clean_tree "$repo_root/out/build/gcc-sanitizers"
clean_tree "$repo_root/out/build/clang-debug"
clean_tree "$repo_root/out/build/clang-sanitizers"
clean_tree "$repo_root/.cache/toolchain-linux-x86_64"

for python_root in "$repo_root/tools" "$repo_root/tests"; do
  find "$python_root" -type f \
    \( -name '*.pyc' -o -name '*.pyo' \) -delete
  find "$python_root" -depth -type d -name __pycache__ -empty -delete
done

rmdir "$repo_root/out/build" 2>/dev/null || true
rmdir "$repo_root/out" 2>/dev/null || true
rmdir "$repo_root/.cache" 2>/dev/null || true

printf '%s\n' "Removed known reproducible local artifacts."
