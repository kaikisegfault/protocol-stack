#!/usr/bin/env python3

import pathlib
import socket
import struct
import subprocess
import sys
import time

MAGIC = b"PSAP"
VERSION = 1
APP_STATE = b'"protocol-stack-v1"'
HEADER = struct.Struct(">4sHBBQI")


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
) -> bytes:
    connection.sendall(
        HEADER.pack(MAGIC, VERSION, 0, kind, request_id, len(payload))
        + payload
    )
    header = receive_exact(connection, HEADER.size)
    magic, version, direction, response_kind, echoed_id, length = (
        HEADER.unpack(header)
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
    status, message_length = struct.unpack(">HI", response[:6])
    if status != 0 or message_length != 0:
        raise RuntimeError(f"application response status {status}")
    return response[6:]


def await_socket(
    process: subprocess.Popen[bytes], socket_path: pathlib.Path
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
) -> subprocess.Popen[bytes]:
    process = subprocess.Popen(
        [executable, database, genesis, socket_path],
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
        try:
            socket_path.unlink()
        except FileNotFoundError:
            pass
        raise


def stop(
    process: subprocess.Popen[bytes], socket_path: pathlib.Path
) -> None:
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
            raise RuntimeError("application ignored SIGTERM")
    error = process.stderr.read().decode("utf-8", "replace")
    if process.returncode != 0:
        raise RuntimeError(
            f"application exit {process.returncode}: {error}"
        )
    if socket_path.exists():
        raise RuntimeError("application retained socket after shutdown")


def connect(socket_path: pathlib.Path) -> socket.socket:
    connection = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    connection.connect(str(socket_path))
    return connection


def remove_outputs(paths: list[pathlib.Path]) -> None:
    for path in paths:
        try:
            path.unlink()
        except FileNotFoundError:
            pass


def verify_genesis_identity(
    executable: pathlib.Path,
    genesis: pathlib.Path,
    chain_id: bytes,
    initial_root: bytes,
) -> None:
    inspected = subprocess.run(
        [executable, "--genesis-identity", genesis],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    expected = (
        f"chain_id={chain_id.hex().upper()}\n"
        f"app_hash={initial_root.hex().upper()}\n"
    ).encode("ascii")
    if inspected.returncode != 0 or inspected.stdout != expected:
        error = inspected.stderr.decode("utf-8", "replace")
        raise RuntimeError(f"genesis identity mismatch: {error}")

    malformed = genesis.with_suffix(".malformed")
    malformed.write_bytes(b"not-canonical-genesis")
    try:
        rejected = subprocess.run(
            [executable, "--genesis-identity", malformed],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if rejected.returncode == 0 or rejected.stdout:
            raise RuntimeError("malformed genesis identity was accepted")
    finally:
        malformed.unlink()


def verify_process(
    executable: pathlib.Path,
    vectors: pathlib.Path,
    prefix: pathlib.Path,
) -> None:
    values = load_values(vectors)
    genesis_bytes = bytes.fromhex(values["genesis"])
    chain_id = bytes.fromhex(values["chain_id"])
    initial_root = bytes.fromhex(values["previous_state_root"])
    database = prefix.with_suffix(".db")
    genesis = prefix.with_suffix(".genesis")
    socket_path = prefix.with_suffix(".sock")
    outputs = [
        database,
        pathlib.Path(f"{database}-journal"),
        pathlib.Path(f"{database}-wal"),
        pathlib.Path(f"{database}-shm"),
        genesis,
        socket_path,
    ]
    remove_outputs(outputs)
    genesis.write_bytes(genesis_bytes)
    verify_genesis_identity(
        executable, genesis, chain_id, initial_root
    )

    first = start(executable, database, genesis, socket_path)
    try:
        with connect(socket_path) as connection:
            info = transact(connection, 1, 1)
            version, height = struct.unpack(">QQ", info[:16])
            if version != 1 or height != 0 or info[16:] != initial_root:
                raise RuntimeError("height-zero Info mismatch")
            init = transact(
                connection,
                2,
                2,
                chain_id
                + struct.pack(">Q", 1)
                + struct.pack(">I", len(APP_STATE))
                + APP_STATE,
            )
            if init != initial_root:
                raise RuntimeError("InitChain root mismatch")
            finalized = transact(
                connection, 6, 3, struct.pack(">QI", 1, 0)
            )
            if len(finalized) != 36 or finalized[32:] != b"\0\0\0\0":
                raise RuntimeError("empty FinalizeBlock mismatch")
            committed = transact(connection, 7, 4)
            committed_height = struct.unpack(">Q", committed[:8])[0]
            if committed_height != 1 or committed[8:] != finalized[:32]:
                raise RuntimeError("Commit mismatch")
            committed_root = committed[8:]
    finally:
        stop(first, socket_path)

    second = start(executable, database, genesis, socket_path)
    try:
        with connect(socket_path) as connection:
            info = transact(connection, 1, 1)
            version, height = struct.unpack(">QQ", info[:16])
            if version != 1 or height != 1 or info[16:] != committed_root:
                raise RuntimeError("restart Info mismatch")
    finally:
        if second.poll() is None:
            second.kill()
            second.wait(timeout=5)
        if second.returncode == 0:
            raise RuntimeError("SIGKILL restart test exited normally")
        if second.stderr is not None:
            second.stderr.close()
        if not socket_path.exists():
            raise RuntimeError("SIGKILL did not leave a stale socket")

    third = start(executable, database, genesis, socket_path)
    try:
        with connect(socket_path) as connection:
            info = transact(connection, 1, 1)
            version, height = struct.unpack(">QQ", info[:16])
            if version != 1 or height != 1 or info[16:] != committed_root:
                raise RuntimeError("stale-socket restart Info mismatch")
            third.terminate()
            try:
                third.wait(timeout=5)
            except subprocess.TimeoutExpired as error:
                raise RuntimeError(
                    "application ignored SIGTERM with an idle client"
                ) from error
    finally:
        stop(third, socket_path)
        remove_outputs(outputs)


def main() -> int:
    if len(sys.argv) != 4:
        raise RuntimeError(
            "usage: headless_process_test "
            "<application> <ledger-vectors> <prefix>"
        )
    verify_process(
        pathlib.Path(sys.argv[1]).resolve(),
        pathlib.Path(sys.argv[2]).resolve(),
        pathlib.Path(sys.argv[3]).resolve(),
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"Headless application test: failed: {error}", file=sys.stderr)
        raise SystemExit(1)
