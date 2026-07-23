#!/bin/sh
set -eu

repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
platform=$(uname -s)
architecture=$(uname -m)

if [ "$platform" != "Linux" ] || [ "$architecture" != "x86_64" ]; then
  echo "unsupported bootstrap platform: $platform $architecture" >&2
  echo "M1 currently supports Linux x86_64" >&2
  exit 1
fi

for command_name in python3 make; do
  if ! command -v "$command_name" >/dev/null 2>&1; then
    echo "missing host prerequisite: $command_name" >&2
    exit 1
  fi
done

preset=${PROTOCOL_STACK_PRESET:-gcc-debug}
toolchain_dir="$repo_root/.cache/toolchain-linux-x86_64"
requirements="$repo_root/tools/toolchain/requirements-linux-x86_64.txt"

if [ ! -x "$toolchain_dir/bin/python" ]; then
  python3 -m venv "$toolchain_dir"
fi

"$toolchain_dir/bin/python" -m pip install \
  --disable-pip-version-check \
  --require-hashes \
  --requirement "$requirements"

PATH="$toolchain_dir/bin:$PATH"
export PATH

cmake --preset "$preset" -S "$repo_root"
cmake --build --preset "$preset"
ctest --preset "$preset" --test-dir "$repo_root/out/build/$preset"
