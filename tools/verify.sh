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

for command_name in python3 make tar; do
  if ! command -v "$command_name" >/dev/null 2>&1; then
    echo "missing host prerequisite: $command_name" >&2
    exit 1
  fi
done

preset=${PROTOCOL_STACK_PRESET:-gcc-debug}
toolchain_dir="$repo_root/.cache/toolchain-linux-x86_64"
requirements="$repo_root/tools/toolchain/requirements-linux-x86_64.txt"
go_bin=$("$repo_root/tools/bootstrap-go.sh")
go_cache="$repo_root/.cache/go-build"
go_module_cache="$repo_root/.cache/go-mod"
go_output="$repo_root/.cache/go-bin"

if [ ! -x "$toolchain_dir/bin/python" ]; then
  python3 -m venv "$toolchain_dir"
fi

"$toolchain_dir/bin/python" -m pip install \
  --disable-pip-version-check \
  --require-hashes \
  --requirement "$requirements"

PATH="$toolchain_dir/bin:$PATH"
export PATH

(
  cd "$repo_root/adapter/cometbft"
  GOTOOLCHAIN=local \
    CGO_ENABLED=0 \
    GOCACHE="$go_cache" \
    GOMODCACHE="$go_module_cache" \
    "$go_bin" mod download
  GOTOOLCHAIN=local \
    CGO_ENABLED=0 \
    GOCACHE="$go_cache" \
    GOMODCACHE="$go_module_cache" \
    "$go_bin" mod verify
  GOTOOLCHAIN=local \
    CGO_ENABLED=0 \
    GOCACHE="$go_cache" \
    GOMODCACHE="$go_module_cache" \
    "$go_bin" test ./...
  GOTOOLCHAIN=local \
    CGO_ENABLED=0 \
    GOCACHE="$go_cache" \
    GOMODCACHE="$go_module_cache" \
    "$go_bin" vet ./...
  mkdir -p "$go_output"
  for command_name in \
    protocol-cometbft-bridge \
    protocol-cometbft-init \
    protocol-cometbft-node; do
    GOTOOLCHAIN=local \
      CGO_ENABLED=0 \
      GOCACHE="$go_cache" \
      GOMODCACHE="$go_module_cache" \
      "$go_bin" build \
        -buildvcs=false \
        -trimpath \
        -o "$go_output/$command_name" \
        "./cmd/$command_name"
  done
)

cmake --preset "$preset" -S "$repo_root"
cmake --build --preset "$preset"
ctest --preset "$preset" --test-dir "$repo_root/out/build/$preset"
"$toolchain_dir/bin/python" \
  "$repo_root/tests/integration/cometbft_single_node_test.py" \
  "$repo_root/out/build/$preset/protocol-application" \
  "$go_output/protocol-cometbft-bridge" \
  "$go_output/protocol-cometbft-init" \
  "$go_output/protocol-cometbft-node" \
  "$repo_root/out/build/$preset/dependencies/libsodium/lib/libsodium.so" \
  "$repo_root/out/build/$preset/integration"
