#!/usr/bin/env python3

"""The version-seven application as a process.

Everything below this line has been exercised in C++ against the recorded
vectors. What has not is the **binary**: that it reads a canonical genesis file
and refuses one that is not canonical, that it prints the two figures an
operator has to put into a consensus engine's configuration, that it creates a
database on first run and reopens it on the second, that it answers the wire on
a private socket, and that it shuts down on SIGTERM and takes its socket with
it.

The figures it is checked against come from
`test-vectors/economy-transition-v7-execution.txt`, which knows nothing about
sockets or processes.
"""

import os
import pathlib
import signal
import socket
import struct
import subprocess
import sys
import time

MAGIC = b"PSAP"
VERSION = 1
APP_STATE = b'"protocol-stack-v7"'
HEADER = struct.Struct(">4sHBBQI")
KIND_INFO = 1
KIND_INIT_CHAIN = 2
KIND_CHECK_TRANSACTION = 3
KIND_COMMIT = 7
SEQUENCE_FAILURE = 3
MALFORMED_TRANSACTION = 1
# magic, schema, chain id, height: the header's previous state root starts here.
HEADER_PREVIOUS_ROOT_OFFSET = 4 + 2 + 32 + 8


def load_values(path: pathlib.Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="ascii").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        key, value = line.split("=", 1)
        values[key] = value
    return values


def receive_exact(connection: socket.socket, size: int) -> bytes:
    result = bytearray()
    while len(result) < size:
        chunk = connection.recv(size - len(result))
        if not chunk:
            raise RuntimeError("unexpected application socket EOF")
        result.extend(chunk)
    return bytes(result)


def transact(
    connection: socket.socket,
    kind: int,
    request_id: int,
    payload: bytes = b"",
) -> tuple[int, bytes]:
    """Send one request frame and return the response's status and body."""
    connection.sendall(
        HEADER.pack(MAGIC, VERSION, 0, kind, request_id, len(payload)) + payload
    )
    header = receive_exact(connection, HEADER.size)
    magic, version, direction, response_kind, echoed_id, length = HEADER.unpack(
        header
    )
    if (
        magic != MAGIC
        or version != VERSION
        or direction != 1
        or response_kind != kind
        or echoed_id != request_id
        or length > 33_554_432
    ):
        raise RuntimeError("invalid application response header")
    response = receive_exact(connection, length)
    if len(response) < 6:
        raise RuntimeError("truncated application response")
    status, reserved = struct.unpack(">HI", response[:6])
    if reserved != 0:
        raise RuntimeError("application response reserved field is not zero")
    return status, response[6:]


def require_ok(
    connection: socket.socket, kind: int, request_id: int, payload: bytes = b""
) -> bytes:
    status, body = transact(connection, kind, request_id, payload)
    if status != 0:
        raise RuntimeError(f"application response status {status}")
    return body


def await_socket(
    process: "subprocess.Popen[bytes]", socket_path: pathlib.Path
) -> None:
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        if socket_path.exists():
            probe = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            try:
                probe.connect(str(socket_path))
                return
            except (ConnectionRefusedError, FileNotFoundError):
                pass
            finally:
                probe.close()
        if process.poll() is not None:
            error = process.stderr.read().decode("utf-8", "replace")
            raise RuntimeError(f"application exited before ready: {error}")
        time.sleep(0.01)
    raise RuntimeError("application socket readiness timeout")


def start(
    executable: pathlib.Path,
    database: pathlib.Path,
    genesis: pathlib.Path,
    socket_path: pathlib.Path,
) -> "subprocess.Popen[bytes]":
    process = subprocess.Popen(
        [str(executable), str(database), str(genesis), str(socket_path)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    try:
        await_socket(process, socket_path)
        if socket_path.stat().st_mode & 0o777 != 0o600:
            raise RuntimeError("application socket is not mode 0600")
        return process
    except Exception:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)
        if process.stderr is not None:
            process.stderr.close()
        raise


def stop(process: "subprocess.Popen[bytes]", socket_path: pathlib.Path) -> None:
    if process.poll() is None:
        process.send_signal(signal.SIGTERM)
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
            raise RuntimeError("application ignored SIGTERM")
    error = process.stderr.read().decode("utf-8", "replace")
    process.stderr.close()
    if process.returncode != 0:
        raise RuntimeError(f"application exit {process.returncode}: {error}")
    if socket_path.exists():
        raise RuntimeError("application retained socket after shutdown")


def connect(socket_path: pathlib.Path) -> socket.socket:
    connection = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    connection.settimeout(10)
    connection.connect(str(socket_path))
    return connection


def blob(payload: bytes) -> bytes:
    return struct.pack(">I", len(payload)) + payload


def init_chain_payload(chain_id: bytes) -> bytes:
    return chain_id + struct.pack(">Q", 1) + blob(APP_STATE)


def run_identity_mode(
    executable: pathlib.Path,
    genesis: pathlib.Path,
    chain_id: bytes,
    genesis_root: bytes,
) -> None:
    result = subprocess.run(
        [str(executable), "--genesis-identity", str(genesis)],
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "identity mode failed: " + result.stderr.decode("utf-8", "replace")
        )
    printed = dict(
        line.split("=", 1)
        for line in result.stdout.decode("ascii").strip().splitlines()
    )
    if printed.get("chain_id") != chain_id.hex().upper():
        raise RuntimeError("identity mode printed a different chain identity")
    # The height-zero state root, which is what a consensus engine records as
    # the application hash before the first block. It is read out of a recorded
    # block header rather than restated here.
    if printed.get("app_hash") != genesis_root.hex().upper():
        raise RuntimeError("identity mode printed a different application hash")


def run_refusals(executable: pathlib.Path, directory: pathlib.Path) -> None:
    """A genesis file that is not canonical must not become a chain."""
    cases = {
        "short.genesis": bytes.fromhex("5053474e0007"),
        "empty.genesis": b"",
    }
    for name, content in cases.items():
        path = directory / name
        path.write_bytes(content)
        result = subprocess.run(
            [str(executable), "--genesis-identity", str(path)],
            capture_output=True,
            check=False,
        )
        if result.returncode == 0:
            raise RuntimeError(f"{name} was accepted as a genesis")


def main() -> int:
    if len(sys.argv) != 4:
        raise SystemExit(
            "usage: headless_process_v7_test.py EXECUTABLE VECTORS DIRECTORY"
        )
    executable = pathlib.Path(sys.argv[1]).resolve()
    values = load_values(pathlib.Path(sys.argv[2]))
    directory = pathlib.Path(sys.argv[3]).resolve()
    if directory.exists():
        for entry in sorted(directory.iterdir()):
            entry.unlink()
    directory.mkdir(parents=True, exist_ok=True)

    genesis_bytes = bytes.fromhex(values["genesis.bytes"])
    chain_id = bytes.fromhex(values["genesis.chain_id"])
    header = bytes.fromhex(values["carried.block0.header"])
    genesis_root = header[
        HEADER_PREVIOUS_ROOT_OFFSET : HEADER_PREVIOUS_ROOT_OFFSET + 32
    ]

    genesis_path = directory / "g"
    genesis_path.write_bytes(genesis_bytes)
    database_path = directory / "d"
    socket_path = directory / "s"
    if len(str(socket_path)) >= 100:
        raise RuntimeError("the test socket pathname is too long for sun_path")

    run_identity_mode(executable, genesis_path, chain_id, genesis_root)
    run_refusals(executable, directory)

    process = start(executable, database_path, genesis_path, socket_path)
    try:
        connection = connect(socket_path)
        try:
            body = require_ok(connection, KIND_INFO, 1)
            version, height = struct.unpack(">QQ", body[:16])
            if version != 7:
                raise RuntimeError("the process reports a foreign protocol version")
            if height != 0:
                raise RuntimeError("a fresh process is not at height zero")
            if body[16:48] != genesis_root:
                raise RuntimeError("the process reports a different genesis root")

            # Committing before the chain is initialised is a status in a
            # well-formed frame, not a broken connection.
            status, _ = transact(connection, KIND_COMMIT, 2)
            if status != SEQUENCE_FAILURE:
                raise RuntimeError("a premature commit was not refused")
        finally:
            connection.close()
    finally:
        stop(process, socket_path)

    if not database_path.exists():
        raise RuntimeError("the first run created no database")

    # A second run reopens what the first created, which is the whole point of
    # the store underneath it, and the chain is initialised over the wire.
    process = start(executable, database_path, genesis_path, socket_path)
    try:
        connection = connect(socket_path)
        try:
            root = require_ok(
                connection, KIND_INIT_CHAIN, 1, init_chain_payload(chain_id)
            )
            if root != genesis_root:
                raise RuntimeError("init_chain answered a different root")
            body = require_ok(
                connection, KIND_CHECK_TRANSACTION, 2, blob(bytes(8))
            )
            (code,) = struct.unpack(">I", body)
            if code != MALFORMED_TRANSACTION:
                raise RuntimeError("rubbish was not refused as malformed")
        finally:
            connection.close()
    finally:
        stop(process, socket_path)

    for entry in sorted(directory.iterdir()):
        entry.unlink()
    print("version-seven headless process: passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
