#!/bin/sh
set -eu

repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
state_root=${PROTOCOL_STACK_DEVNET_ROOT:-"$repo_root/.local/devnet"}
preset=${PROTOCOL_STACK_PRESET:-gcc-debug}
base_port=${PROTOCOL_STACK_DEVNET_BASE_P2P_PORT:-27656}
toolchain_dir="$repo_root/.cache/toolchain-linux-x86_64"
go_output="$repo_root/.cache/go-bin"
application="$repo_root/out/build/$preset/protocol-application"
devnet="$go_output/protocol-cometbft-devnet"
bridge="$go_output/protocol-cometbft-bridge"
node="$go_output/protocol-cometbft-node"
genesis="$state_root/protocol.genesis"

usage() {
  printf '%s\n' \
    "usage: tools/devnet.sh start" \
    "       tools/devnet.sh health" \
    "       tools/devnet.sh transaction <hex-file> [node-index]" \
    "" \
    "start remains in the foreground; press Ctrl-C for an orderly stop."
}

require_platform() {
  platform=$(uname -s)
  architecture=$(uname -m)
  if [ "$platform" != "Linux" ] || [ "$architecture" != "x86_64" ]; then
    echo "unsupported devnet platform: $platform $architecture" >&2
    exit 1
  fi
  for command_name in python3 make tar; do
    if ! command -v "$command_name" >/dev/null 2>&1; then
      echo "missing host prerequisite: $command_name" >&2
      exit 1
    fi
  done
}

ensure_binaries() {
  if [ -x "$application" ] &&
     [ -x "$devnet" ] &&
     [ -x "$bridge" ] &&
     [ -x "$node" ]; then
    return
  fi
  require_platform
  echo "Building the focused devnet binaries on first use." >&2
  echo "This downloads pinned build, Go, libsodium, and SQLite inputs." >&2

  requirements="$repo_root/tools/toolchain/requirements-linux-x86_64.txt"
  go_bin=$("$repo_root/tools/bootstrap-go.sh")
  go_cache="$repo_root/.cache/go-build"
  go_module_cache="$repo_root/.cache/go-mod"
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
    mkdir -p "$go_output"
    for command_name in \
      protocol-cometbft-bridge \
      protocol-cometbft-devnet \
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
  cmake --build --preset "$preset" --target protocol_application_server
}

decode_hex_once() {
  source_path=$1
  target_path=$2
  python3 - "$source_path" "$target_path" <<'PY'
import os
import pathlib
import sys

source = pathlib.Path(sys.argv[1])
target = pathlib.Path(sys.argv[2])
try:
    decoded = bytes.fromhex(source.read_text(encoding="ascii"))
except (OSError, ValueError) as error:
    raise SystemExit(f"decode {source}: {error}") from error
target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
os.chmod(target.parent, 0o700)
if target.exists():
    if not target.is_file() or target.read_bytes() != decoded:
        raise SystemExit(f"existing {target} differs from {source}")
else:
    target.write_bytes(decoded)
    os.chmod(target, 0o600)
PY
}

if [ "$#" -lt 1 ]; then
  usage >&2
  exit 1
fi

command_name=$1
shift
case "$command_name" in
  start)
    if [ "$#" -ne 0 ]; then
      usage >&2
      exit 1
    fi
    ensure_binaries
    decode_hex_once \
      "$repo_root/examples/devnet/protocol.genesis.hex" \
      "$genesis"
    exec "$devnet" start \
      -root "$state_root" \
      -base-p2p-port "$base_port" \
      -genesis "$genesis" \
      -application "$application" \
      -bridge "$bridge" \
      -node "$node"
    ;;
  health)
    if [ "$#" -ne 0 ]; then
      usage >&2
      exit 1
    fi
    ensure_binaries
    exec "$devnet" health \
      -root "$state_root" \
      -base-p2p-port "$base_port"
    ;;
  transaction)
    if [ "$#" -lt 1 ] || [ "$#" -gt 2 ]; then
      usage >&2
      exit 1
    fi
    ensure_binaries
    transaction_hex=$1
    node_index=${2:-0}
    transaction_file=$(mktemp "$state_root/.transaction.XXXXXX")
    trap 'rm -f "$transaction_file"' EXIT HUP INT TERM
    python3 - "$transaction_hex" "$transaction_file" <<'PY'
import pathlib
import sys

source = pathlib.Path(sys.argv[1])
target = pathlib.Path(sys.argv[2])
try:
    target.write_bytes(bytes.fromhex(source.read_text(encoding="ascii")))
except (OSError, ValueError) as error:
    raise SystemExit(f"decode {source}: {error}") from error
PY
    "$devnet" transaction \
      -root "$state_root" \
      -base-p2p-port "$base_port" \
      -node-index "$node_index" \
      -tx-file "$transaction_file"
    ;;
  *)
    usage >&2
    exit 1
    ;;
esac
