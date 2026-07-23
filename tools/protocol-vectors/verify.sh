#!/bin/sh
set -eu

repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
build_dir=$(mktemp -d)
trap 'rm -rf "$build_dir"' EXIT HUP INT TERM

cxx=${CXX:-c++}
"$cxx" -std=c++20 -Wall -Wextra -Wpedantic -Werror \
  "$repo_root/tools/protocol-vectors/verify.cpp" \
  -o "$build_dir/verify_cpp" -Wl,-l:libsodium.so.23

"$build_dir/verify_cpp" \
  "$repo_root/test-vectors/protocol-primitives-v1.txt"
python3 "$repo_root/tools/protocol-vectors/verify.py" \
  "$repo_root/test-vectors/protocol-primitives-v1.txt"
